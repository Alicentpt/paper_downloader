"""Download helpers for arXiv papers and source archives."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import arxiv
import requests

from ..utils import sanitize_filename

ARXIV_HEADERS = {"User-Agent": "Mozilla/5.0 paper_downloader/0.1"}
ARXIV_TIMEOUT = 60
DEFAULT_PDF_DIR = Path("./papers/PDFs")
DEFAULT_LATEX_DIR = Path("./papers/LaTeX")


def ensure_output_dirs(
    pdf_dir: str | Path = DEFAULT_PDF_DIR,
    latex_dir: str | Path = DEFAULT_LATEX_DIR,
) -> tuple[Path, Path]:
    """Create the output directories used by arXiv downloads and return them."""
    pdf_path = Path(pdf_dir)
    latex_path = Path(latex_dir)
    pdf_path.mkdir(parents=True, exist_ok=True)
    latex_path.mkdir(parents=True, exist_ok=True)
    return pdf_path, latex_path


def build_arxiv_file_stem(result: arxiv.Result) -> str:
    """Build a stable file stem from an arXiv result identifier and title."""
    short_id = result.get_short_id().replace("/", "_")
    title = sanitize_filename(result.title, fallback=short_id).replace(" ", "_")
    if title == short_id:
        return short_id
    return f"{short_id}.{title}"


def download_result_pdf(result: arxiv.Result, pdf_dir: Path) -> Path:
    """Download a single arXiv PDF into the target PDF directory."""
    response = requests.get(
        result.pdf_url,
        headers=ARXIV_HEADERS,
        timeout=ARXIV_TIMEOUT,
    )
    response.raise_for_status()

    pdf_path = pdf_dir / f"{build_arxiv_file_stem(result)}.pdf"
    pdf_path.write_bytes(response.content)
    return pdf_path


def download_result_source(result: arxiv.Result, latex_dir: Path) -> Path | None:
    """Download the source archive for a single arXiv result when available."""
    source_url = f"https://arxiv.org/e-print/{result.get_short_id()}"

    try:
        response = requests.get(
            source_url,
            headers=ARXIV_HEADERS,
            timeout=ARXIV_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    source_path = latex_dir / f"{build_arxiv_file_stem(result)}.tar.gz"
    source_path.write_bytes(response.content)
    return source_path


def build_download_record(
    result: arxiv.Result,
    pdf_path: Path,
    source_path: Path | None,
) -> dict[str, str | None]:
    """Build a CLI- and API-friendly record for one arXiv download."""
    return {
        "paper_id": result.get_short_id(),
        "title": result.title,
        "pdf_path": str(pdf_path),
        "source_path": str(source_path) if source_path else None,
    }


def extract_arxiv_id_from_url(url: str) -> str:
    """Extract the arXiv identifier from an `/abs/...` or `/pdf/...` URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    for prefix in ("abs/", "pdf/"):
        if not path.startswith(prefix):
            continue

        paper_id = path[len(prefix) :]
        if paper_id.endswith(".pdf"):
            paper_id = paper_id[:-4]
        if paper_id:
            return paper_id

    raise ValueError(f"Unsupported arXiv URL: {url}")


def download_arxiv_query(
    query: str,
    max_results: int = 10,
    sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance,
    pdf_dir: str | Path = DEFAULT_PDF_DIR,
    latex_dir: str | Path = DEFAULT_LATEX_DIR,
) -> list[dict[str, str | None]]:
    """Download PDFs and source archives for an arXiv search query."""
    pdf_path, latex_path = ensure_output_dirs(pdf_dir=pdf_dir, latex_dir=latex_dir)
    search = arxiv.Search(query=query, max_results=max_results, sort_by=sort_by)
    client = arxiv.Client()

    downloads = []
    for result in client.results(search):
        downloaded_pdf = download_result_pdf(result, pdf_path)
        downloaded_source = download_result_source(result, latex_path)
        downloads.append(build_download_record(result, downloaded_pdf, downloaded_source))

    return downloads


def download_arxiv_paper(
    paper_id: str,
    pdf_dir: str | Path = DEFAULT_PDF_DIR,
    latex_dir: str | Path = DEFAULT_LATEX_DIR,
) -> dict[str, str | None]:
    """Download a single arXiv paper by identifier."""
    pdf_path, latex_path = ensure_output_dirs(pdf_dir=pdf_dir, latex_dir=latex_dir)
    result = next(arxiv.Client().results(arxiv.Search(id_list=[paper_id])))
    downloaded_pdf = download_result_pdf(result, pdf_path)
    downloaded_source = download_result_source(result, latex_path)
    return build_download_record(result, downloaded_pdf, downloaded_source)


def download_arxiv_paper_from_url(
    url: str,
    pdf_dir: str | Path = DEFAULT_PDF_DIR,
    latex_dir: str | Path = DEFAULT_LATEX_DIR,
) -> dict[str, str | None]:
    """Download a single arXiv paper from an arXiv URL."""
    return download_arxiv_paper(
        extract_arxiv_id_from_url(url),
        pdf_dir=pdf_dir,
        latex_dir=latex_dir,
    )
