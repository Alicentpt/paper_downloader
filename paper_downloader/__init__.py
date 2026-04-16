"""Public package API for paper_downloader."""

from .scrappers.arxiv import (
    DEFAULT_LATEX_DIR,
    DEFAULT_PDF_DIR,
    download_arxiv_paper,
    download_arxiv_paper_from_url,
    download_arxiv_query,
    extract_arxiv_id_from_url,
)
from .scrappers.scihub import CaptchaNeedException, SciHub, download_scihub_paper, download_scihub_query

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

__version__ = "0.1.0"
