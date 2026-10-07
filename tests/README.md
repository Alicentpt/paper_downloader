# MCP acceptance scenarios

Run `python -m pytest tests` after installing `.[mcp,dev]`. Tests use generated
responses and local processes; publisher availability is a separate manual check.
There was no tracked test suite before this change.

## PD-MCP-001 — Installed stdio contract

Given an installed package and a working directory outside its checkout,
when an MCP client initializes, lists tools, and sends invalid download arguments,
then it receives the advertised tools and a protocol error without losing the session.

Oracle: the MCP SDK client and explicit expected public tool names. Detects broken
entry points, import/cwd dependence, stdout contamination, and missing validation.
Test: `tests/test_mcp_protocol.py::test_installed_stdio_contract`.
Overlap: adapter tests also exercise tool errors, but not installation/transport.

## PD-MCP-002 — Downloader interoperability

Given a fake external downloader with an explicit result,
when an MCP download tool is called with absolute output directories,
then its structured result contains the returned paths; a backend failure becomes
an MCP tool error rather than a successful download.

Oracle: an independent fixed record or raised exception at the existing API boundary.
Detects broken argument/result wiring and false success reporting.
Test: `tests/test_mcp_tools.py::test_download_tool` (backend variants).
Overlap: PD-MCP-001 covers transport, not network backend wiring.

## PD-MCP-003 — Search without downloading

Given a Crossref response with a known DOI and total count,
when a bounded journal-article bibliographic search is requested,
then its metadata and pagination information are returned without writing files.
HTTP failures must propagate as errors.

Oracle: a fixed Crossref payload and a requests HTTP error.
Test: `tests/test_crossref.py::test_crossref_metadata` and `test_crossref_http_error`.
Detects response corruption and treating failed requests as empty successful searches.
No overlapping metadata-search coverage.

## PD-MCP-004 — Direct PDF integrity

Given a streamed HTTP response,
when downloading a direct PDF into an absolute directory,
then valid PDF bytes are saved with a content-addressed filename; HTML and
oversized payloads fail without leaving partial files or damaging existing files.

Oracle: fixed bytes and SHA256 from Python's standard library. Parameterized
negative controls vary only payload validity or the byte limit.
Test: `tests/test_direct_pdf.py::test_direct_pdf`.
Detects login pages masquerading as PDFs, partial publication and filename collisions.
No overlapping persistence coverage; downloader wiring mocks the storage boundary.

## Manual network smoke

Use the MCP SDK or an attached client to search `clinochlore` with `search_crossref`.
Download a known arXiv record into a durable research directory with
`download_arxiv_paper`. Confirm PDF magic, page count and the reported source path.
This checks live provider availability; it is not a deterministic CI acceptance test.

## PD-ARXIV-005 — PDF-only submissions have no source archive

Given an arXiv e-print endpoint that responds with PDF bytes or an HTML page,
when source retrieval is requested,
then the downloader returns `None` and writes no mislabeled source archive.
A gzip response still produces the original source bytes on disk.

Oracle: independent fixed PDF/HTML bytes and a standard-library gzip payload,
with exact byte comparison for the accepted case.
Test: `tests/test_arxiv_source.py::test_source_payload_kind`.
Detects the observed arXiv 2206.09943v1 PDF response being saved as `.tar.gz`.
Overlap: MCP wiring tests mock this backend and do not check source response kinds.
