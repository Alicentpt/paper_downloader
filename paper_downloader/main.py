"""Command-line interface for downloading papers from arXiv and Sci-Hub."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import arxiv

from .scrappers.arxiv import (
    DEFAULT_LATEX_DIR,
    DEFAULT_PDF_DIR,
    download_arxiv_paper,
    download_arxiv_paper_from_url,
    download_arxiv_query,
)
from .scrappers.scihub import download_scihub_paper, download_scihub_query

SORT_BY_CHOICES = {
    "relevance": arxiv.SortCriterion.Relevance,
    "submitted_date": arxiv.SortCriterion.SubmittedDate,
    "last_updated_date": arxiv.SortCriterion.LastUpdatedDate,
}


def add_pdf_dir_argument(parser: argparse.ArgumentParser) -> None:
    """Add the common PDF output argument to a parser."""
    parser.add_argument(
        "--pdf-dir",
        default=str(DEFAULT_PDF_DIR),
        help="directory where downloaded PDFs will be saved",
    )


def add_arxiv_output_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the common arXiv output directory arguments to a parser."""
    add_pdf_dir_argument(parser)
    parser.add_argument(
        "--latex-dir",
        default=str(DEFAULT_LATEX_DIR),
        help="directory where downloaded arXiv source archives will be saved",
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level CLI parser and its subcommands."""
    parser = argparse.ArgumentParser(
        prog="paper-downloader",
        description="Download papers from arXiv and Sci-Hub.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    arxiv_query_parser = subparsers.add_parser(
        "arxiv-query",
        help="download multiple papers from an arXiv query",
    )
    arxiv_query_parser.add_argument("query", help="arXiv query string")
    arxiv_query_parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="maximum number of papers to download",
    )
    arxiv_query_parser.add_argument(
        "--sort-by",
        choices=sorted(SORT_BY_CHOICES),
        default="relevance",
        help="arXiv sort criterion",
    )
    add_arxiv_output_arguments(arxiv_query_parser)
    arxiv_query_parser.set_defaults(handler=run_arxiv_query)

    arxiv_paper_parser = subparsers.add_parser(
        "arxiv-paper",
        help="download one paper from an arXiv identifier",
    )
    arxiv_paper_parser.add_argument("paper_id", help="arXiv identifier")
    add_arxiv_output_arguments(arxiv_paper_parser)
    arxiv_paper_parser.set_defaults(handler=run_arxiv_paper)

    arxiv_url_parser = subparsers.add_parser(
        "arxiv-url",
        help="download one paper from an arXiv URL",
    )
    arxiv_url_parser.add_argument("url", help="arXiv `/abs/...` or `/pdf/...` URL")
    add_arxiv_output_arguments(arxiv_url_parser)
    arxiv_url_parser.set_defaults(handler=run_arxiv_url)

    scihub_paper_parser = subparsers.add_parser(
        "scihub-paper",
        help="download one paper through Sci-Hub",
    )
    identifier_group = scihub_paper_parser.add_mutually_exclusive_group(required=True)
    identifier_group.add_argument("--paper-id", help="DOI or PMID to resolve via Sci-Hub")
    identifier_group.add_argument("--url", help="paywalled article URL to resolve via Sci-Hub")
    add_pdf_dir_argument(scihub_paper_parser)
    scihub_paper_parser.set_defaults(handler=run_scihub_paper)

    scihub_query_parser = subparsers.add_parser(
        "scihub-query",
        help="search Google Scholar and download matching papers through Sci-Hub",
    )
    scihub_query_parser.add_argument("query", help="Google Scholar query string")
    scihub_query_parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="maximum number of papers to download",
    )
    add_pdf_dir_argument(scihub_query_parser)
    scihub_query_parser.set_defaults(handler=run_scihub_query)

    return parser


def run_arxiv_query(args: argparse.Namespace) -> list[dict[str, str | None]]:
    """Handle the `arxiv-query` subcommand."""
    return download_arxiv_query(
        query=args.query,
        max_results=args.max_results,
        sort_by=SORT_BY_CHOICES[args.sort_by],
        pdf_dir=args.pdf_dir,
        latex_dir=args.latex_dir,
    )


def run_arxiv_paper(args: argparse.Namespace) -> list[dict[str, str | None]]:
    """Handle the `arxiv-paper` subcommand."""
    return [
        download_arxiv_paper(
            paper_id=args.paper_id,
            pdf_dir=args.pdf_dir,
            latex_dir=args.latex_dir,
        )
    ]


def run_arxiv_url(args: argparse.Namespace) -> list[dict[str, str | None]]:
    """Handle the `arxiv-url` subcommand."""
    return [
        download_arxiv_paper_from_url(
            url=args.url,
            pdf_dir=args.pdf_dir,
            latex_dir=args.latex_dir,
        )
    ]


def run_scihub_paper(args: argparse.Namespace) -> list[dict[str, str | None]]:
    """Handle the `scihub-paper` subcommand."""
    return [
        download_scihub_paper(
            paper_id=args.paper_id,
            url=args.url,
            pdf_dir=args.pdf_dir,
        )
    ]


def run_scihub_query(args: argparse.Namespace) -> list[dict[str, str | None]]:
    """Handle the `scihub-query` subcommand."""
    return download_scihub_query(
        query=args.query,
        max_results=args.max_results,
        pdf_dir=args.pdf_dir,
    )


def print_records(records: list[dict[str, str | None]]) -> None:
    """Print download records in a readable, stable order."""
    for index, record in enumerate(records):
        for key, value in record.items():
            if value is None:
                continue
            print(f"{key}: {value}")
        if index != len(records) - 1:
            print()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a shell-friendly exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        records = args.handler(args)
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print_records(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
