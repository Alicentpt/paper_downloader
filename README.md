# paper_downloader

`paper_downloader` downloads papers from arXiv and Sci-Hub through a CLI and Python
API. Its optional **MCP server** adds Crossref metadata search and direct PDF
downloads for agent clients.

The code is split by responsibility:

- `paper_downloader/utils/` contains PDF title extraction helpers for no title/metadata Sci-hub papers
- `paper_downloader/scrappers/arxiv.py` contains arXiv download logic
- `paper_downloader/scrappers/scihub.py` contains Sci-Hub search and download logic
- `paper_downloader/main.py` contains the CLI entrypoint

## Installation

### Conda environment

By default when installing with `pip install`, all requirements will be installed. If you want dedicated conda env, use:

```bash
conda env create -f environment.yml
conda activate paper_downloader
```

### Editable install with CLI entrypoint

Install the project so the `paper-downloader` command is available:

```bash
pip install -e .
```

This uses the package metadata in `pyproject.toml`.

## CLI usage

You can run the CLI in either of these ways:

```bash
paper-downloader --help
python -m paper_downloader --help
```

### Download one arXiv paper by id

```bash
paper-downloader arxiv-paper 2112.14193
```

### Download one arXiv paper by URL

```bash
paper-downloader arxiv-url https://arxiv.org/abs/2112.14193
```

### Download several arXiv papers from a query

```bash
paper-downloader arxiv-query "all:quantum chemistry" --max-results 3
paper-downloader arxiv-query "cat:quant-ph" --sort-by submitted_date --max-results 5
paper-downloader arxiv-query "review of biological imaging" --max-results 1
```

`arxiv-query` also accepts plain-language, non-category searches such as `"review of biological imaging"`, not only explicit `all:` or `cat:` filters.

Observed results from my validation runs:

- `paper-downloader arxiv-query "all:quantum chemistry" --max-results 1`
  returned `2112.14193v3`:
  `A full circuit-based quantum algorithm for excited-states in quantum chemistry`
- `paper-downloader arxiv-query "review of biological imaging" --max-results 1`
  returned `1007.4471v1`:
  `The physical language of molecular codes: A rate-distortion approach to the evolution and emergence of biological codes`

### Download one paper through Sci-Hub by DOI or PMID

```bash
paper-downloader scihub-paper --paper-id 10.1038/nphys1170
```

### Download one paper through Sci-Hub by article URL

```bash
paper-downloader scihub-paper --url "https://www.sciencedirect.com/science/article/abs/pii/S0009261403006924"
```

### Search via Google Scholar and download through Sci-Hub

```bash
paper-downloader scihub-query "quantum chemistry" --max-results 3
```

`scihub-query` first prints the found Google Scholar results, then downloads them one by one with a 10 second delay between attempts. Use `--download-delay N` to change that pause. Per-paper failures are printed and recorded without stopping the rest of the batch.

`scihub-query` depends on Google Scholar result pages. If Scholar blocks the request, use `scihub-paper` with a DOI or URL instead.

## Output directories

By default the CLI writes to:

- PDFs: `./papers/PDFs`
- arXiv sources: `./papers/LaTeX`

You can override them:

```bash
paper-downloader arxiv-paper 2112.14193 --pdf-dir "$HOME/research/papers/PDFs" --latex-dir "$HOME/research/papers/LaTeX"
paper-downloader scihub-paper --paper-id 10.1038/nphys1170 --pdf-dir "$HOME/research/papers/PDFs"
```

## Python API

```python
from paper_downloader import (
    SciHub,
    download_arxiv_paper,
    download_arxiv_paper_from_url,
    download_arxiv_query,
    download_scihub_paper,
    download_scihub_query,
)

download_arxiv_paper("2112.14193")
download_arxiv_paper_from_url("https://arxiv.org/abs/2112.14193")
download_arxiv_query("all:quantum chemistry", max_results=2)

download_scihub_paper(paper_id="10.1038/nphys1170")
download_scihub_paper(
    url="https://www.sciencedirect.com/science/article/abs/pii/S0009261403006924"
)
```

Each public function returns a dictionary or list of dictionaries with the written file paths.

## MCP server

Install the optional MCP dependency in a dedicated environment from this checkout:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[mcp]'
```

Connect it to **OpenCode V2** using an absolute executable path:

```bash
opencode mcp add paper-downloader --global -- "$(pwd)/.venv/bin/paper-downloader-mcp"
opencode mcp list
```

The command writes the connection; `/mcps` shows its live status. The server is
launched by the client over stdio, so no separate daemon or port is needed.
`python -m paper_downloader.mcp_server` is an equivalent module entry point.

For manual configuration, merge this object into `mcp.servers` in your existing
OpenCode config, replacing `/absolute/path` with your actual checkout location:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "paper-downloader": {
        "type": "local",
        "command": ["/absolute/path/paper_downloader/.venv/bin/paper-downloader-mcp"]
      }
    }
  }
}
```

### Tools

| Tool | Purpose | Required arguments |
| --- | --- | --- |
| `search_crossref` | Journal-article metadata search; up to 20 results with offset pagination | `query` |
| `download_arxiv_paper` | arXiv PDF plus source archive if available | `paper_id`, `pdf_dir`, `latex_dir` |
| `download_arxiv_query` | Search arXiv and download up to 20 results; default 5 | `query`, `pdf_dir`, `latex_dir` |
| `download_paper` | Existing Sci-Hub downloader for a DOI, PMID or article URL | `identifier`, `pdf_dir` |
| `download_pdf` | Direct HTTP(S) PDF; 100 MiB limit and SHA256 filename | `url`, `pdf_dir` |

Every download requires **absolute output directories**. Use durable directories
inside the research workspace. The tool returns structured paths and metadata,
not the PDF content. Crossref returns its original JSON envelope:
`message.items` holds records, `message.total-results` holds the total count.
Use `max_results` (1–20) and `offset` (0–1000) for additional pages. Searches filter
to Crossref's `journal-article` type to exclude review reports, book entries and
standalone supplementary records. Matching is relevance-ranked, not an exhaustive
subject bibliography; inspect each title and DOI.

### Errors and current limits

HTTP errors, unavailable mirrors and invalid arguments become MCP tool errors.
Downloads run in a worker thread and serialize writes within one server; protocol
messages remain responsive. Cancelling a request does not interrupt an in-flight
blocking HTTP operation. Request timeouts are 30 seconds for Crossref and up to
60 seconds per direct-PDF read; existing backend retries still apply.

Direct downloads validate PDF magic and size, remove incomplete files, and use
content-addressed filenames. They do not parse the entire PDF for validity.
The existing arXiv/Sci-Hub APIs retain their own filename, overwrite and validation
behavior. An arXiv batch can leave already completed files after an error; it is
not transactional. An unavailable arXiv source is represented by `source_path: null`.
PDF-only submissions and HTML responses from arXiv's e-print endpoint are also
reported as unavailable sources rather than saved as misleading `.tar.gz` files.

Search metadata is not evidence that a paper's full text was read. Crossref does
not enumerate every repository or resolve open-access PDF URLs. Google Scholar
batch search remains available through the CLI and may encounter blocking pages.

## Development checks

Install `.[mcp,dev]`, then run:

```bash
python -m ruff check paper_downloader/mcp_server.py paper_downloader/mcp_downloads.py paper_downloader/clients paper_downloader/scrappers/arxiv.py tests
python -m ruff format --check paper_downloader/mcp_server.py paper_downloader/mcp_downloads.py paper_downloader/clients paper_downloader/scrappers/arxiv.py tests
python -m pyright
python -m pytest tests -q
```

These gates cover the MCP/HTTP modules, the changed arXiv backend and their
acceptance tests. The remaining CLI/scraper files are imported and exercised at the adapter boundary but have not
received a repository-wide style migration. GitHub Actions runs these checks on
every push and pull request under Python 3.11 and 3.13, plus a CLI startup check.

The portable Ruff config extends the unmodified user baseline captured on
2026-10-07 in `config/ruff-baseline.toml` (SHA256
`37a101a86bf67f2b45723bafb5c9aee1e95702008eab7098dedc4354e5c9fa68`).
The policy additions are absolute imports and missing annotations; explicit
first-party import classification keeps checks independent of the working directory.
The Python target is 3.11 to match package support. See [acceptance scenarios](tests/README.md)
for guarantees, independent oracles and intentional integration overlap.

[`SKILL.md`](SKILL.md) documents the CLI and MCP workflow for agents.
