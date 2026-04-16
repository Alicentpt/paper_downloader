"""Sci-Hub integration used by the package API and CLI."""

from __future__ import annotations

import hashlib
import logging
import os
import pathlib
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import requests
import urllib3
from bs4 import BeautifulSoup
from retrying import retry

from ..utils import extract_pdf_title, sanitize_filename

logging.basicConfig()
logger = logging.getLogger("Sci-Hub")
logger.setLevel(logging.DEBUG)

urllib3.disable_warnings()

SCHOLARS_BASE_URL = "https://scholar.google.com/scholar"
SCIHUB_MIRROR_SOURCE_URL = "https://sci-hub.now.sh/"
DEFAULT_SCIHUB_URLS = [
    "https://www.sci-hub.ru",
    "https://www.sci-hub.st",
    "https://sci-hub.tw",
    "https://sci-hub.ee",
    "https://sci-hub.do",
]
REQUEST_TIMEOUT = 30
DEFAULT_PDF_DIR = Path("./papers/PDFs")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    )
}
BLOCKED_RESPONSE_MARKERS = (
    "captcha",
    "unusual traffic",
    "just a moment",
    "attention required",
    "cloudflare",
)


class SciHub:
    """Fetch paper PDFs from Sci-Hub mirrors and search Google Scholar results."""

    def __init__(self):
        """Initialize an HTTP session and choose the first available mirror."""
        self.sess = requests.Session()
        self.sess.headers.update(HEADERS)
        self.available_base_url_list = self._get_available_scihub_urls()
        if not self.available_base_url_list:
            raise RuntimeError("Could not find any working Sci-Hub mirrors")
        self.base_url = self.available_base_url_list[0] + "/"

    def _get_available_scihub_urls(self) -> list[str]:
        """Return a deduplicated list of Sci-Hub mirrors to try."""
        urls = list(DEFAULT_SCIHUB_URLS)

        try:
            response = requests.get(SCIHUB_MIRROR_SOURCE_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            logger.info(
                "Failed to refresh Sci-Hub mirrors from %s: %s",
                SCIHUB_MIRROR_SOURCE_URL,
                error,
            )
            return self._unique_urls(urls)

        redirected_mirror = self._normalize_base_url(response.url)
        if redirected_mirror:
            urls.append(redirected_mirror)

        soup = self._get_soup(response.content)
        for anchor in soup.find_all("a", href=True):
            normalized = self._normalize_base_url(anchor["href"])
            if normalized:
                urls.append(normalized)

        return self._unique_urls(urls)

    def set_proxy(self, proxy: str) -> None:
        """Configure an HTTP(S) proxy for the current session."""
        if proxy:
            self.sess.proxies = {"http": proxy, "https": proxy}

    def _change_base_url(self) -> None:
        """Switch the active mirror to the next URL in the local mirror list."""
        current_base_url = self.base_url.rstrip("/")
        self.available_base_url_list = [
            url for url in self.available_base_url_list if url != current_base_url
        ]
        if not self.available_base_url_list:
            raise RuntimeError("Ran out of valid sci-hub urls")
        self.base_url = self.available_base_url_list[0] + "/"
        logger.info("Changing mirror to %s", self.available_base_url_list[0])

    def search(self, query: str, limit: int = 10, download: bool = False) -> dict:
        """Search Google Scholar and return candidate paper links."""
        del download

        start = 0
        results = {"papers": []}

        while True:
            try:
                response = self.sess.get(
                    SCHOLARS_BASE_URL,
                    params={"q": query, "start": start},
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.exceptions.RequestException:
                results["err"] = (
                    "Failed to complete search with query %s (connection error)" % query
                )
                return results

            if self._is_blocked_response(response):
                results["err"] = (
                    "Failed to complete search with query %s "
                    "(Google Scholar blocked the request)"
                ) % query
                return results

            soup = self._get_soup(response.content)
            papers = soup.select("div.gs_r, div.gs_or")
            if not papers:
                return results

            previous_count = len(results["papers"])

            for paper in papers:
                title = paper.select_one("h3.gs_rt")
                if title is None:
                    continue

                pdf_link = paper.select_one("div.gs_ggs.gs_fl a")
                title_link = title.find("a")

                source = None
                if pdf_link is not None:
                    source = pdf_link.get("href")
                elif title_link is not None:
                    source = title_link.get("href")

                if not source:
                    continue

                results["papers"].append(
                    {"name": title.get_text(strip=True), "url": source}
                )
                if len(results["papers"]) >= limit:
                    return results

            if len(results["papers"]) == previous_count:
                return results

            start += 10

    @retry(wait_random_min=100, wait_random_max=1000, stop_max_attempt_number=10)
    def download(
        self,
        identifier: str,
        destination: str = "",
        path: str | None = None,
    ) -> dict:
        """Download a single paper PDF to the requested destination path."""
        data = self.fetch(identifier)
        if not data:
            data = {"err": "Failed to fetch pdf with identifier %s" % identifier}

        if "err" not in data:
            self._save(data["pdf"], os.path.join(destination, path or data["name"]))

        return data

    def fetch(self, identifier: str) -> dict:
        """Resolve and download a paper PDF without saving it to disk yet."""
        id_type = self._classify(identifier)
        original_base_url = self.base_url
        candidate_base_urls = [original_base_url.rstrip("/")] + [
            url
            for url in self.available_base_url_list
            if url != original_base_url.rstrip("/")
        ]
        max_attempts = 1 if id_type == "url-direct" else len(candidate_base_urls)
        last_error = None

        for attempt in range(max_attempts):
            if id_type != "url-direct":
                self.base_url = candidate_base_urls[attempt] + "/"

            resolved_url = None
            try:
                resolved_url = self._get_direct_url(identifier)
                if not resolved_url:
                    raise CaptchaNeedException(
                        "Failed to resolve a direct pdf url for %s via %s"
                        % (identifier, self.base_url.rstrip("/"))
                    )

                response = self.sess.get(
                    resolved_url,
                    verify=False,
                    timeout=REQUEST_TIMEOUT,
                )

                if self._is_pdf_response(response):
                    return {
                        "pdf": response.content,
                        "url": resolved_url,
                        "name": self._generate_name(response),
                    }

                if self._is_blocked_response(response):
                    raise CaptchaNeedException(
                        "Failed to fetch pdf with identifier %s "
                        "(resolved url %s) due to captcha or anti-bot protection"
                        % (identifier, resolved_url)
                    )

                raise CaptchaNeedException(
                    "Resolved url %s did not return a PDF for identifier %s"
                    % (resolved_url, identifier)
                )

            except (CaptchaNeedException, requests.exceptions.ConnectionError) as error:
                last_error = str(error)
            except requests.exceptions.RequestException as error:
                last_error = (
                    "Failed to fetch pdf with identifier %s (resolved url %s): %s"
                    % (identifier, resolved_url, error)
                )

        self.base_url = original_base_url
        return {"err": last_error or "Failed to fetch pdf with identifier %s" % identifier}

    def _get_direct_url(self, identifier: str) -> str | None:
        """Return the resolved PDF URL for a DOI, PMID, or article URL."""
        id_type = self._classify(identifier)
        if id_type == "url-direct":
            return identifier
        return self._search_direct_url(identifier)

    def _search_direct_url(self, identifier: str) -> str | None:
        """Parse a Sci-Hub landing page and extract the embedded PDF URL."""
        response = self.sess.get(
            self.base_url + identifier,
            verify=False,
            timeout=REQUEST_TIMEOUT,
        )

        soup = self._get_soup(response.content)
        meta_pdf = soup.find("meta", attrs={"name": "citation_pdf_url"})
        if meta_pdf is not None:
            candidate = self._normalize_download_url(meta_pdf.get("content"))
            if candidate and self._looks_like_pdf_url(candidate):
                return candidate

        for tag_name, attribute in (("iframe", "src"), ("embed", "src"), ("object", "data")):
            for tag in soup.find_all(tag_name):
                candidate = self._normalize_download_url(tag.get(attribute))
                if candidate and self._looks_like_pdf_url(candidate):
                    return candidate

        match = re.search(
            r"((?:https?:)?//[^\"'\\s>]+\.pdf(?:#[^\"'\\s>]*)?)",
            response.text,
            flags=re.IGNORECASE,
        )
        if match:
            return self._normalize_download_url(match.group(1))

        if self._is_blocked_response(response):
            raise CaptchaNeedException(
                "Mirror %s blocked access to %s" % (self.base_url.rstrip("/"), identifier)
            )

        return None

    def _classify(self, identifier: str) -> str:
        """Classify an identifier as a direct URL, article URL, PMID, or DOI."""
        if identifier.startswith("http") or identifier.startswith("https"):
            return "url-direct" if identifier.endswith("pdf") else "url-non-direct"
        if identifier.isdigit():
            return "pmid"
        return "doi"

    def _save(self, data: bytes, path: str) -> None:
        """Persist downloaded PDF bytes to disk."""
        destination = pathlib.Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    def _get_soup(self, html: bytes) -> BeautifulSoup:
        """Parse HTML content into a BeautifulSoup document."""
        return BeautifulSoup(html, "html.parser")

    def _generate_name(self, response: requests.Response) -> str:
        """Generate a mostly stable fallback filename from the response URL and bytes."""
        name = response.url.split("/")[-1]
        name = re.sub(r"#view=(.+)", "", name)
        pdf_hash = hashlib.md5(response.content).hexdigest()
        return "%s-%s" % (pdf_hash, name[-20:])

    def _normalize_base_url(self, url: str | None) -> str | None:
        """Normalize a Sci-Hub mirror URL into `scheme://host` form."""
        if not url:
            return None

        candidate = url.strip()
        if candidate.startswith("//"):
            candidate = "https:" + candidate
        elif "://" not in candidate:
            candidate = "https://" + candidate.lstrip("/")

        parsed = urlparse(candidate)
        if "sci-hub." not in parsed.netloc:
            return None

        return f"{parsed.scheme}://{parsed.netloc}"

    def _unique_urls(self, urls: list[str]) -> list[str]:
        """Return the input mirror URLs in first-seen order without duplicates."""
        unique_urls = []
        seen = set()

        for url in urls:
            normalized = self._normalize_base_url(url)
            if normalized and normalized not in seen:
                unique_urls.append(normalized)
                seen.add(normalized)

        return unique_urls

    def _normalize_download_url(self, url: str | None) -> str | None:
        """Convert a relative or protocol-relative PDF URL into an absolute URL."""
        if not url:
            return None

        if url.startswith("//"):
            return "https:" + url

        parsed = urlparse(url)
        if parsed.scheme:
            return url

        return urljoin(self.base_url, url)

    def _looks_like_pdf_url(self, url: str) -> bool:
        """Return `True` when a resolved URL likely points to a PDF resource."""
        normalized_url = url.lower()
        return ".pdf" in normalized_url or "/pdf/" in normalized_url

    def _is_pdf_response(self, response: requests.Response) -> bool:
        """Return `True` when an HTTP response body looks like a PDF."""
        content_type = response.headers.get("Content-Type", "").lower()
        return "application/pdf" in content_type or response.content.startswith(b"%PDF-")

    def _is_blocked_response(self, response: requests.Response) -> bool:
        """Return `True` when a response looks like anti-bot or rate-limit protection."""
        if response.status_code in {403, 429, 503, 504}:
            return True

        response_text = response.text.lower()
        return any(marker in response_text for marker in BLOCKED_RESPONSE_MARKERS)


class CaptchaNeedException(Exception):
    """Raised when a Sci-Hub or Scholar response looks like bot protection."""


def ensure_pdf_dir(pdf_dir: str | Path = DEFAULT_PDF_DIR) -> Path:
    """Create the PDF output directory used by Sci-Hub downloads and return it."""
    output_dir = Path(pdf_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def finalize_scihub_download(
    temp_pdf_path: Path,
    fallback_name: str,
    pdf_dir: Path,
) -> Path:
    """Rename a temporary Sci-Hub PDF using the best available extracted title."""
    title = extract_pdf_title(temp_pdf_path)
    fallback_stem = Path(fallback_name).stem or "downloaded_paper"
    final_name = sanitize_filename(title, fallback=fallback_stem)
    final_pdf_path = pdf_dir / f"{final_name}.pdf"

    if final_pdf_path.exists():
        existing_hash = hashlib.sha256(final_pdf_path.read_bytes()).hexdigest()
        new_hash = hashlib.sha256(temp_pdf_path.read_bytes()).hexdigest()
        if existing_hash == new_hash:
            temp_pdf_path.unlink()
            return final_pdf_path

    os.replace(temp_pdf_path, final_pdf_path)
    return final_pdf_path


def build_download_record(
    identifier: str,
    resolved_url: str | None,
    pdf_path: Path,
    source_name: str | None,
    query_name: str | None = None,
) -> dict[str, str | None]:
    """Build a CLI- and API-friendly record for one Sci-Hub download."""
    record = {
        "identifier": identifier,
        "resolved_url": resolved_url,
        "pdf_path": str(pdf_path),
        "path": str(pdf_path),
        "source_name": source_name,
    }
    if query_name is not None:
        record["query_name"] = query_name
    return record


def download_scihub_paper(
    paper_id: str | None = None,
    url: str | None = None,
    pdf_dir: str | Path = DEFAULT_PDF_DIR,
) -> dict[str, str | None]:
    """Download one paper through Sci-Hub using either an identifier or a URL."""
    identifier = paper_id or url
    if not identifier:
        raise ValueError("Either paper_id or url must be provided")

    output_dir = ensure_pdf_dir(pdf_dir)
    temp_pdf_path = output_dir / f"temp_download_{uuid4().hex}.pdf"
    scihub = SciHub()
    result = scihub.download(identifier, path=str(temp_pdf_path))

    if not result or "err" in result:
        raise RuntimeError((result or {}).get("err", "Sci-Hub download failed"))

    final_pdf_path = finalize_scihub_download(
        temp_pdf_path=temp_pdf_path,
        fallback_name=result.get("name", "downloaded_paper"),
        pdf_dir=output_dir,
    )

    return build_download_record(
        identifier=identifier,
        resolved_url=result.get("url"),
        pdf_path=final_pdf_path,
        source_name=result.get("name"),
    )


def download_scihub_query(
    query: str,
    max_results: int = 10,
    pdf_dir: str | Path = DEFAULT_PDF_DIR,
) -> list[dict[str, str | None]]:
    """Search Google Scholar and download the returned papers through Sci-Hub."""
    ensure_pdf_dir(pdf_dir)
    scihub = SciHub()
    results = scihub.search(query, max_results)

    if "err" in results:
        raise RuntimeError(results["err"])

    downloads = []
    for paper in results["papers"]:
        download_record = download_scihub_paper(url=paper["url"], pdf_dir=pdf_dir)
        download_record["query_name"] = paper["name"]
        downloads.append(download_record)

    return downloads
