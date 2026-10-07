"""MCP download adapters over the existing package APIs and direct HTTP client."""

from functools import partial
from typing import Annotated

from anyio import Lock, to_thread
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from paper_downloader.clients.direct_pdf import absolute_output_dir, download_pdf
from paper_downloader.scrappers import arxiv, scihub

Nonempty = Annotated[str, Field(min_length=1)]
ResultCount = Annotated[int, Field(ge=1, le=20)]


def register_download_tools(server: FastMCP) -> None:
    """
    Register download tools with serialized writes and responsive stdio.

    Args:
        server: MCP server that owns these tool registrations.

    Existing backends may write the same title-based file. Serialize downloads
    within one server and run blocking HTTP outside the protocol event loop.
    """
    lock = Lock()

    @server.tool(name="download_arxiv_paper")
    async def arxiv_paper(
        paper_id: Nonempty, pdf_dir: Nonempty, latex_dir: Nonempty
    ) -> dict[str, str | None]:
        """
        Download an arXiv paper and its source archive when available.

        Args:
            paper_id: arXiv identifier, optionally including a version suffix.
            pdf_dir: Absolute directory for the PDF.
            latex_dir: Absolute directory for the source archive.

        Returns:
            Title, identifier and file paths; source_path is null if unavailable.
        """
        operation = partial(
            arxiv.download_arxiv_paper,
            paper_id,
            pdf_dir=absolute_output_dir(pdf_dir),
            latex_dir=absolute_output_dir(latex_dir),
        )
        async with lock:
            return await to_thread.run_sync(operation)

    @server.tool(name="download_arxiv_query")
    async def arxiv_query(
        query: Nonempty,
        pdf_dir: Nonempty,
        latex_dir: Nonempty,
        max_results: ResultCount = 5,
    ) -> list[dict[str, str | None]]:
        """
        Search arXiv and download up to 20 results, ranked by relevance.

        Args:
            query: arXiv query, with plain-language or arXiv field syntax.
            pdf_dir: Absolute directory for PDFs.
            latex_dir: Absolute directory for source archives.
            max_results: Maximum number of downloads, from 1 to 20.

        Returns:
            Download records; source_path may be null. A batch failure is an
            error, and files completed before that error remain on disk.
        """
        operation = partial(
            arxiv.download_arxiv_query,
            query,
            max_results=max_results,
            pdf_dir=absolute_output_dir(pdf_dir),
            latex_dir=absolute_output_dir(latex_dir),
        )
        async with lock:
            return await to_thread.run_sync(operation)

    @server.tool(name="download_paper")
    async def paper(identifier: Nonempty, pdf_dir: Nonempty) -> dict[str, str | None]:
        """
        Download a DOI, PMID or article URL through the existing Sci-Hub backend.

        Args:
            identifier: DOI, PMID or publisher article URL.
            pdf_dir: Absolute directory for the PDF.

        Returns:
            Resolved URL and file paths. Mirror or access failures are tool errors.
        """
        operation = partial(
            scihub.download_scihub_paper,
            paper_id=identifier,
            pdf_dir=absolute_output_dir(pdf_dir),
        )
        async with lock:
            return await to_thread.run_sync(operation)

    @server.tool(name="download_pdf")
    async def direct_pdf(url: Nonempty, pdf_dir: Nonempty) -> dict[str, str]:
        """
        Download a direct PDF URL, with a 100 MiB limit and SHA256 filename.

        Args:
            url: HTTP(S) PDF URL, such as a publisher's open-access endpoint.
            pdf_dir: Absolute directory for the PDF.

        Returns:
            Original/resolved URLs, absolute PDF path and SHA256; HTML is rejected.
        """
        async with lock:
            return await to_thread.run_sync(partial(download_pdf, url, pdf_dir))
