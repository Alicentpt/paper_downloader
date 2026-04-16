"""Backward-compatible exports for the Sci-Hub integration."""

from .scrappers.scihub import CaptchaNeedException, SciHub, download_scihub_paper, download_scihub_query

__all__ = [
    "CaptchaNeedException",
    "SciHub",
    "download_scihub_paper",
    "download_scihub_query",
]
