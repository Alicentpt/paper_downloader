"""Stream direct PDFs to bounded, content-addressed local artifacts."""

import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import requests

MAX_PDF_BYTES = 100 * 1024 * 1024


def absolute_output_dir(directory: str) -> Path:
    """
    Validate an explicit output location without creating it.

    Args:
        directory: Absolute output directory; a leading tilde is expanded.

    Returns:
        Absolute path independent of the server's working directory.

    Raises:
        ValueError: The path is relative.
    """
    path = Path(directory).expanduser()
    if not path.is_absolute():
        raise ValueError("Output directories must be absolute")
    return path


def download_pdf(
    url: str, pdf_dir: str, max_bytes: int = MAX_PDF_BYTES
) -> dict[str, str]:
    """
    Save a direct HTTP(S) PDF after checking its magic and size.

    Args:
        url: Direct PDF endpoint, not an article landing page.
        pdf_dir: Absolute destination directory.
        max_bytes: Maximum streamed bytes, default 100 MiB.

    Returns:
        Original and resolved URLs, absolute PDF path and full SHA256 digest.

    Raises:
        ValueError: URL, size bound or output path is invalid, or the response
            does not start with PDF magic or exceeds the byte budget.

    HTTP and filesystem errors propagate. Partial files are removed on failure.
    Magic validation rejects HTML, but is not a complete PDF parser validation.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or max_bytes < 1:
        raise ValueError("Supply an HTTP(S) URL and a positive byte limit")
    directory = absolute_output_dir(pdf_dir)
    directory.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with requests.get(url, stream=True, timeout=(15, 60)) as response:
            response.raise_for_status()
            digest = hashlib.sha256()
            size = 0
            with NamedTemporaryFile(dir=directory, suffix=".part", delete=False) as out:
                temporary = Path(out.name)
                for chunk in response.iter_content(chunk_size=65536):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError("PDF exceeds the download byte limit")
                    digest.update(chunk)
                    out.write(chunk)
            with temporary.open("rb") as saved:
                if saved.read(5) != b"%PDF-":
                    raise ValueError("Response is not a PDF (missing %PDF- header)")
            destination = directory / f"paper-{digest.hexdigest()}.pdf"
            temporary.replace(destination)
            return {
                "url": url,
                "resolved_url": response.url,
                "pdf_path": str(destination),
                "sha256": digest.hexdigest(),
            }
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
