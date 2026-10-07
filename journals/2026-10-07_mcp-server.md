# Goal

Expose paper discovery and existing downloads through a stdio MCP server, with
explicit output directories and structured success/error results.

# Context

The starting commit was `4c35f2f`. The package already offered an arXiv/Sci-Hub CLI
and Python functions, but no tracked MCP server, tests or CI workflow.
The motivating research task was a literature search on clinochlore DFT.

# Method

The optional `mcp` extra provides the transport dependency. The server registers
five tools, reusing the existing arXiv/Sci-Hub functions and adding small HTTP
clients for Crossref metadata and direct PDFs. Download writes are serialized
per server; blocking requests run off the protocol event loop.

Acceptance scenarios PD-MCP-001 through PD-MCP-004 were written before the code.
The suite exercises installed stdio from outside the checkout, backend integration,
metadata preservation, error propagation, bounded PDF publication and cleanup.

# Results

- Python 3.13 final local validation: **13 tests passed**, with one existing PyPDF2
  deprecation warning. Python 3.11 and 3.13 are configured in the new GitHub CI.
- Ruff 0.15.4 check and format check passed for all new Python modules and tests.
  The global autofix script was used with the portable baseline overlay.
- Pyright 1.1.408 basic passed with zero errors/warnings using the MCP environment
  explicitly via `--pythonpath`. CLI `--help` and `git diff --check` passed.
- A real stdio client searched Crossref and downloaded the publisher PDF for
  DOI `10.1038/s41699-025-00540-w`. Its SHA256 was
  `5baaa974b9344efbc67f4186288b7d58c7d5d3bf94b1a1690258f80fbb9a26a4`.
- A PMC endpoint returned HTML instead of PDF; the MCP tool correctly returned an
  error without publishing a PDF. The existing DOI downloader subsequently
  retrieved the requested article. A separate arXiv request encountered HTTP 429.

Live discovery initially returned many Crossref review-report and supplementary
records. The final search uses `filter=type:journal-article` to make its scope
explicit and improve the first result page. This does not make the query exhaustive.

Artifact inspection also found that the original arXiv e-print helper saved a
PDF-only submission as `.tar.gz`. PD-ARXIV-005 was written before the repair:
PDF and HTML source responses now return `None` without publishing an archive.
The changed arXiv module was added to the same Ruff/Pyright/CI scope, its public
docstrings completed, and missing PDF-URL metadata now raises a clear ValueError.

# Takeaways

The MCP adapter is ready for client connection. Provider availability is not
guaranteed by the deterministic tests. Search metadata and downloaded full text
remain distinct evidence types.

The new suite has one intentional overlap: tool-error behavior is tested at the
adapter boundary and at installed stdio, where packaging/stdout can fail separately.
No unrelated existing test suite was available to review for overlap. Existing
scraper-wide lint/type cleanup and full parser validation of PDFs are outside this
change; their behavior remains documented in the README.
