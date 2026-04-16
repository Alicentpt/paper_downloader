"""Download backends used by the paper downloader package."""

from .arxiv import (
    DEFAULT_LATEX_DIR,
    DEFAULT_PDF_DIR,
    download_arxiv_paper,
    download_arxiv_paper_from_url,
    download_arxiv_query,
    extract_arxiv_id_from_url,
)
from .scihub import CaptchaNeedException, SciHub, download_scihub_paper, download_scihub_query

__all__ = [
    "CaptchaNeedException",
    "DEFAULT_LATEX_DIR",
    "DEFAULT_PDF_DIR",
    "SciHub",
    "download_arxiv_paper",
    "download_arxiv_paper_from_url",
    "download_arxiv_query",
    "download_scihub_paper",
    "download_scihub_query",
    "extract_arxiv_id_from_url",
]
