"""Optional stdio MCP entry point for paper discovery and downloads."""

from functools import partial
from typing import Annotated

from anyio import to_thread
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field, JsonValue

from paper_downloader.clients.crossref import search_crossref
from paper_downloader.mcp_downloads import (
    Nonempty,
    ResultCount,
    register_download_tools,
)


def create_server() -> FastMCP:
    """
    Build the MCP catalog without performing network access.

    Returns:
        A stdio-ready server with metadata search and explicit-directory downloads.
    """
    server = FastMCP(
        "paper-downloader",
        instructions=(
            "Search Crossref for bibliographic metadata, then download selected papers. "
            "Metadata alone is not full text. Pass absolute, durable output directories "
            "in the research workspace. Downloads return paths, not document content. "
            "Use direct PDF URLs for open access, arXiv tools for preprints, or "
            "download_paper for the existing Sci-Hub backend. Network failures are "
            "tool errors; do not claim an unsuccessful download was saved."
        ),
    )

    @server.tool(name="search_crossref", annotations=ToolAnnotations(readOnlyHint=True))
    async def metadata(
        query: Nonempty,
        max_results: ResultCount = 10,
        offset: Annotated[int, Field(ge=0, le=1000)] = 0,
    ) -> dict[str, JsonValue]:
        """
        Search Crossref journal articles without downloading any papers.

        Args:
            query: Bibliographic query, title or subject terms.
            max_results: Number of results, from 1 to 20.
            offset: Result offset for pagination, from 0 to 1000.

        Returns:
            Crossref envelope with message.items and message.total-results.
            Items contain DOI, title, authors, date and URL when provided by Crossref.
        """
        return await to_thread.run_sync(
            partial(search_crossref, query, max_results, offset)
        )

    register_download_tools(server)
    return server


def main() -> None:
    """Serve MCP on stdin/stdout; backend diagnostics use stderr."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
