"""
Tests for web_search tool (Tavily integration).

Covers:
  1. Returns fallback message when TAVILY_API_KEY is empty
  2. Calls TavilyClient.search() with correct args when key is set
  3. Maps Tavily response fields (title, url, content) to expected keys
  4. Respects max_results parameter
  5. Handles empty results list gracefully
  6. Handles Tavily API error gracefully

Patch targets — both are lazy-imported inside web_search():
  - `tavily.TavilyClient`   (from tavily import TavilyClient)
  - `api.config.settings`   (from api.config import settings)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tavily_response(n: int) -> dict:
    return {
        "results": [
            {
                "title": f"Title {i}",
                "url": f"https://example.com/{i}",
                "content": f"Snippet {i}",
            }
            for i in range(n)
        ]
    }


def _mock_settings(api_key: str = "tvly-abc", base_url: str = "https://api.tavily.com") -> MagicMock:
    s = MagicMock()
    s.tavily_api_key = api_key
    s.tavily_base_url = base_url
    return s


# ---------------------------------------------------------------------------
# 1. No API key → fallback message, no HTTP call made
# ---------------------------------------------------------------------------

def test_web_search_returns_fallback_when_no_api_key():
    with patch("tavily.TavilyClient") as mock_cls, \
         patch("api.config.settings", _mock_settings(api_key="")):

        from agent_runtime.tools.builtin import web_search
        result = web_search("test query")

    mock_cls.assert_not_called()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "web_search not configured"
    assert result[0]["url"] == ""


# ---------------------------------------------------------------------------
# 2. Valid key → TavilyClient instantiated with correct args
# ---------------------------------------------------------------------------

def test_web_search_creates_client_with_correct_args():
    mock_client = MagicMock()
    mock_client.search.return_value = _make_tavily_response(3)

    with patch("tavily.TavilyClient", return_value=mock_client) as mock_cls, \
         patch("api.config.settings", _mock_settings("tvly-abc123", "https://custom.tavily.com")):

        from agent_runtime.tools.builtin import web_search
        web_search("AI news")

    mock_cls.assert_called_once_with(
        api_key="tvly-abc123",
        api_base_url="https://custom.tavily.com",
    )


# ---------------------------------------------------------------------------
# 3. Response fields mapped correctly (title, url, content → snippet)
# ---------------------------------------------------------------------------

def test_web_search_maps_response_fields():
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {"title": "My Title", "url": "https://foo.com", "content": "My snippet"}
        ]
    }

    with patch("tavily.TavilyClient", return_value=mock_client), \
         patch("api.config.settings", _mock_settings()):

        from agent_runtime.tools.builtin import web_search
        result = web_search("test")

    assert len(result) == 1
    assert result[0] == {"title": "My Title", "url": "https://foo.com", "snippet": "My snippet"}


# ---------------------------------------------------------------------------
# 4. max_results passed through to client.search()
# ---------------------------------------------------------------------------

def test_web_search_passes_max_results():
    mock_client = MagicMock()
    mock_client.search.return_value = _make_tavily_response(2)

    with patch("tavily.TavilyClient", return_value=mock_client), \
         patch("api.config.settings", _mock_settings()):

        from agent_runtime.tools.builtin import web_search
        web_search("query", max_results=2)

    mock_client.search.assert_called_once_with("query", max_results=2)


# ---------------------------------------------------------------------------
# 5. Empty results list → returns []
# ---------------------------------------------------------------------------

def test_web_search_handles_empty_results():
    mock_client = MagicMock()
    mock_client.search.return_value = {"results": []}

    with patch("tavily.TavilyClient", return_value=mock_client), \
         patch("api.config.settings", _mock_settings()):

        from agent_runtime.tools.builtin import web_search
        result = web_search("obscure query")

    assert result == []


# ---------------------------------------------------------------------------
# 6. Tavily API raises → exception propagates (agent runtime handles it)
# ---------------------------------------------------------------------------

def test_web_search_propagates_tavily_errors():
    import pytest

    mock_client = MagicMock()
    mock_client.search.side_effect = Exception("Tavily 429: rate limited")

    with patch("tavily.TavilyClient", return_value=mock_client), \
         patch("api.config.settings", _mock_settings()):

        from agent_runtime.tools.builtin import web_search

        with pytest.raises(Exception, match="429"):
            web_search("query")
