# paper_downloader

`paper_downloader` is a small Python package and CLI for downloading papers from arXiv and Sci-Hub.

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
paper-downloader arxiv-paper 2112.14193 --pdf-dir /tmp/pdfs --latex-dir /tmp/latex
paper-downloader scihub-paper --paper-id 10.1038/nphys1170 --pdf-dir /tmp/pdfs
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

## Development notes

- `paper_downloader/SKILL.md` teaches an agent how to use the CLI correctly.
