"""Bounded bibliographic searches against the public Crossref REST API."""

import requests
from pydantic import JsonValue, TypeAdapter

JSON_OBJECT = TypeAdapter(dict[str, JsonValue])
MAX_RESULTS = 20
MAX_OFFSET = 1000


def search_crossref(
    query: str, max_results: int = 10, offset: int = 0
) -> dict[str, JsonValue]:
    """
    Search metadata without downloading papers or assuming full-text access.

    Args:
        query: Nonempty bibliographic query, including titles or subject terms.
        max_results: Number of records, from 1 to 20.
        offset: Result offset, from 0 to 1000.

    Returns:
        Crossref envelope with DOI, title, authors, publication date, URL and
        pagination metadata. Missing publisher metadata remains missing.

    Raises:
        ValueError: The query or result bounds are invalid.

    HTTP and JSON validation errors propagate to the caller.
    """
    if (
        not query.strip()
        or not 1 <= max_results <= MAX_RESULTS
        or not 0 <= offset <= MAX_OFFSET
    ):
        raise ValueError("Supply a query, 1..20 results and an offset of 0..1000")
    response = requests.get(
        "https://api.crossref.org/works",
        params={
            "query.bibliographic": query,
            "rows": max_results,
            "offset": offset,
            "select": "DOI,title,author,published,URL",
        },
        headers={"User-Agent": "paper_downloader MCP (Crossref metadata search)"},
        timeout=30,
    )
    response.raise_for_status()
    return JSON_OBJECT.validate_python(response.json())
