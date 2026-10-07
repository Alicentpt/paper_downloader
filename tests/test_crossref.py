"""Crossref metadata behavior using controlled HTTP responses."""

from unittest.mock import Mock

import pytest
import requests

from paper_downloader.clients import crossref


def test_crossref_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """PD-MCP-003: retain DOI and pagination from a bounded metadata response."""
    payload = {"message": {"total-results": 27, "items": [{"DOI": "10.1234/example"}]}}
    response = Mock(spec=requests.Response)
    response.json.return_value = payload
    get = Mock(return_value=response)
    monkeypatch.setattr(crossref.requests, "get", get)
    assert crossref.search_crossref("clinochlore", 3, 6) == payload
    assert get.call_args.kwargs["params"] == {
        "query.bibliographic": "clinochlore",
        "rows": 3,
        "offset": 6,
        "select": "DOI,title,author,published,URL",
    }


def test_crossref_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """PD-MCP-003: HTTP failures cannot masquerade as an empty result set."""
    response = Mock(spec=requests.Response)
    response.raise_for_status.side_effect = requests.HTTPError("rate limited")
    monkeypatch.setattr(crossref.requests, "get", Mock(return_value=response))
    with pytest.raises(requests.HTTPError, match="rate limited"):
        crossref.search_crossref("clinochlore")
