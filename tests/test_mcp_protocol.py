"""Installed-process checks for the public stdio MCP contract."""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_installed_stdio_contract(tmp_path: Path) -> None:
    """PD-MCP-001: installation, validation and errors preserve protocol health."""

    async def exercise() -> None:
        """Use the real installed console script from an unrelated directory."""
        parameters = StdioServerParameters(
            command=str(Path(sys.executable).parent / "paper-downloader-mcp"),
            cwd=str(tmp_path),
        )
        async with (
            stdio_client(parameters) as (reader, writer),
            ClientSession(reader, writer) as session,
        ):
            await session.initialize()
            catalog = await session.list_tools()
            assert {tool.name for tool in catalog.tools} == {
                "search_crossref",
                "download_arxiv_paper",
                "download_arxiv_query",
                "download_paper",
                "download_pdf",
            }
            invalid = await session.call_tool(
                "download_pdf", {"url": "https://example.org/a.pdf", "pdf_dir": "."}
            )
            assert invalid.isError
            assert "absolute" in str(invalid.content)
            bounded = await session.call_tool(
                "search_crossref", {"query": "test", "max_results": 21}
            )
            assert bounded.isError
            await session.send_ping()
            assert list(tmp_path.iterdir()) == []

    asyncio.run(asyncio.wait_for(exercise(), timeout=30))
