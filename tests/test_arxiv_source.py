"""Source availability for arXiv submissions with different response kinds."""

import gzip
from pathlib import Path
from unittest.mock import Mock

import arxiv
import pytest
import requests

from paper_downloader.scrappers import arxiv as downloader


@pytest.mark.parametrize(
    ("payload", "content_type", "available"),
    [
        (b"%PDF-1.7\nsubmitted PDF", "application/octet-stream", False),
        (b"<html>challenge</html>", "text/html; charset=utf-8", False),
        (gzip.compress(b"\\documentclass{article}"), "application/gzip", True),
    ],
    ids=["pdf-only", "html-challenge", "gzip-source"],
)
def test_source_payload_kind(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: bytes,
    content_type: str,
    available: bool,
) -> None:
    """PD-ARXIV-005: unavailable sources never become mislabeled archives."""
    metadata = Mock(spec=arxiv.Result)
    metadata.get_short_id.return_value = "2206.09943v1"
    metadata.title = "Example paper"
    response = Mock(spec=requests.Response)
    response.content = payload
    response.headers = {"Content-Type": content_type}
    monkeypatch.setattr(downloader.requests, "get", Mock(return_value=response))
    path = downloader.download_result_source(metadata, tmp_path)
    if available:
        assert path is not None
        assert path.read_bytes() == payload
    else:
        assert path is None
        assert list(tmp_path.iterdir()) == []
