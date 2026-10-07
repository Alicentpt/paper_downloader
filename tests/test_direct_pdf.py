"""Persistent direct-PDF integrity at the streaming HTTP boundary."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
import requests

from paper_downloader.clients import direct_pdf


@pytest.mark.parametrize(
    ("body", "limit", "error"),
    [
        (b"%PDF-1.7\nexample", 100, None),
        (b"<html>Login required</html>", 100, "not a PDF"),
        (b"%PDF-1.7\nexample", 8, "byte limit"),
    ],
    ids=["pdf", "html-login", "too-large"],
)
def test_direct_pdf(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    body: bytes,
    limit: int,
    error: str | None,
) -> None:
    """PD-MCP-004: publish bounded PDF bytes and clean up rejected responses."""
    existing = tmp_path / "existing.pdf"
    existing.write_bytes(b"preserve me")
    response = MagicMock(spec=requests.Response)
    response.__enter__.return_value = response
    response.iter_content.return_value = [body[:3], body[3:]]
    response.url = "https://example.org/resolved.pdf"
    monkeypatch.setattr(direct_pdf.requests, "get", Mock(return_value=response))
    if error:
        with pytest.raises(ValueError, match=error):
            direct_pdf.download_pdf("https://example.org/a.pdf", str(tmp_path), limit)
        assert list(tmp_path.iterdir()) == [existing]
    else:
        result = direct_pdf.download_pdf(
            "https://example.org/a.pdf", str(tmp_path), limit
        )
        assert Path(result["pdf_path"]).read_bytes() == body
        assert result["sha256"] == hashlib.sha256(body).hexdigest()
        assert result["resolved_url"] == response.url
    assert existing.read_bytes() == b"preserve me"
    assert list(tmp_path.glob("*.part")) == []
