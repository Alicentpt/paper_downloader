"""Adapter checks at external downloader boundaries."""

import asyncio
from pathlib import Path
from unittest.mock import Mock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from paper_downloader import mcp_downloads
from paper_downloader.mcp_server import create_server


@pytest.mark.parametrize(
    ("tool", "backend", "argument"),
    [
        ("download_paper", "scihub", "identifier"),
        ("download_arxiv_paper", "arxiv", "paper_id"),
        ("download_arxiv_query", "arxiv", "query"),
        ("download_pdf", "direct", "url"),
    ],
    ids=["doi", "arxiv-id", "arxiv-search", "direct-pdf"],
)
def test_download_tool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tool: str,
    backend: str,
    argument: str,
) -> None:
    """PD-MCP-002: preserve backend results and surface failed downloads."""
    record = {"pdf_path": str(tmp_path / "paper.pdf")}
    expected = [record] if tool == "download_arxiv_query" else record
    download = Mock(return_value=expected)
    owner = mcp_downloads if backend == "direct" else getattr(mcp_downloads, backend)
    function = "download_scihub_paper" if backend == "scihub" else tool
    monkeypatch.setattr(owner, function, download)
    arguments = {argument: "test-id", "pdf_dir": str(tmp_path)}
    if backend == "arxiv":
        arguments["latex_dir"] = str(tmp_path / "sources")
    server = create_server()
    result = asyncio.run(server.call_tool(tool, arguments))
    # FastMCP returns text plus structured content; its current annotation omits
    # this tuple shape. Check it at the SDK boundary before reading the payload.
    assert isinstance(result, tuple)
    assert result[1] == (
        {"result": expected} if isinstance(expected, list) else expected
    )
    if backend == "direct":
        download.assert_called_once_with("test-id", str(tmp_path))
    else:
        assert download.call_args.kwargs["pdf_dir"] == tmp_path
    download.side_effect = RuntimeError("provider unavailable")
    with pytest.raises(ToolError, match="provider unavailable"):
        asyncio.run(server.call_tool(tool, arguments))
