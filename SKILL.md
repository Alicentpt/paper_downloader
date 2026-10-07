---
name: paper-downloader-cli
description: Use this skill when you need to download papers from the local `paper_downloader` project through its CLI, choose the correct arXiv or Sci-Hub command, or verify where downloads will be written.
---

# Paper Downloader CLI

Use this skill from the project root: `paper_downloader/`.

## Setup

Create and activate the environment:

```bash
conda env create -f environment.yml
conda activate paper_downloader
```

Install the package in editable mode so the CLI entrypoint is available:

```bash
pip install -e .
```

## Command Selection

- Use `paper-downloader arxiv-paper <paper_id>` for a known arXiv identifier.
- Use `paper-downloader arxiv-url <url>` for a direct arXiv `/abs/...` or `/pdf/...` URL.
- Use `paper-downloader arxiv-query "<query>" --max-results N` for batch arXiv downloads.
  Plain-language queries such as `"review of biological imaging"` are supported in addition to `all:` or `cat:` syntax.
- Use `paper-downloader scihub-paper --paper-id <doi>` for a DOI or PMID through Sci-Hub.
- Use `paper-downloader scihub-paper --url <article_url>` for a paywalled publisher URL through Sci-Hub.
- Use `paper-downloader scihub-query "<query>" --max-results N` only when the user explicitly wants Scholar-style search results.

## Output Directories

- PDFs default to `./papers/PDFs`
- arXiv source archives default to `./papers/LaTeX`
- Override them with `--pdf-dir` and `--latex-dir`

## MCP Interface

Install the optional extra with `pip install -e '.[mcp]'` in a dedicated
environment, then configure the client to run `paper-downloader-mcp` over stdio.
See the README for the OpenCode V2 connection command.

- `search_crossref` searches journal-article metadata without downloading; paginate with `offset`.
- `download_arxiv_paper` downloads an identifier; `download_arxiv_query` downloads search results.
- `download_paper` accepts a DOI, PMID or article URL through the existing Sci-Hub backend.
- `download_pdf` saves a direct HTTP(S) PDF with a SHA256 filename and 100 MiB limit.

Supply absolute, durable `pdf_dir` and, for arXiv, `latex_dir` paths. Inspect tool
errors before reporting success. Download records are paths and metadata, not
full-text contents; open the saved paper before attributing detailed methods to it.

## Workflow Notes

- Prefer the CLI for user-facing tasks and the Python API for embedding in scripts.
- `scihub-query` depends on Google Scholar HTML and can fail with a block page. If that happens, fall back to `scihub-paper`.
- Sci-Hub mirrors change over time. Retry once before assuming the code is broken.
- Tested plain-language arXiv queries also work.
  `paper-downloader arxiv-query "all:quantum chemistry" --max-results 1` returned `2112.14193v3`.
  `paper-downloader arxiv-query "review of biological imaging" --max-results 1` returned `1007.4471v1`.

## Example Commands

```bash
paper-downloader arxiv-paper 2112.14193
paper-downloader arxiv-query "all:quantum chemistry" --max-results 3
paper-downloader arxiv-query "review of biological imaging" --max-results 1
paper-downloader scihub-paper --paper-id 10.1038/nphys1170
paper-downloader scihub-paper --url "https://www.sciencedirect.com/science/article/abs/pii/S0009261403006924"
```
