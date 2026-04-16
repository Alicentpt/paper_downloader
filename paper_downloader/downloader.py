"""Backward-compatible exports for the public downloader helpers."""

from .scrappers.arxiv import (
    DEFAULT_LATEX_DIR,
    DEFAULT_PDF_DIR,
    download_arxiv_paper,
    download_arxiv_paper_from_url,
    download_arxiv_query,
    extract_arxiv_id_from_url,
)
from .scrappers.scihub import download_scihub_paper, download_scihub_query

__all__ = [
    "DEFAULT_LATEX_DIR",
    "DEFAULT_PDF_DIR",
    "download_arxiv_paper",
    "download_arxiv_paper_from_url",
    "download_arxiv_query",
    "download_scihub_paper",
    "download_scihub_query",
    "extract_arxiv_id_from_url",
]
