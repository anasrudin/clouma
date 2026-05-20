"""
Builtin starter tools for Clouma agent runtime.

These 4 tools are auto-registered when agent_runtime.tools is imported.
Stub implementations are marked; real implementations use standard library
or lightweight HTTP client (httpx).

Security note for read_file: this is unsandboxed — any path accessible to the
process can be read.  Sandboxing / path allow-listing is a Phase 7+ concern.
"""

from __future__ import annotations

import zoneinfo
from datetime import datetime
from pathlib import Path

import httpx

from . import register_tool


# ---------------------------------------------------------------------------
# web_search
# ---------------------------------------------------------------------------


@register_tool(
    name="web_search",
    description=(
        "Search the web for a query and return a list of results, each with "
        "title, url, and snippet fields."
    ),
)
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for the given query.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        A list of dicts, each with keys: title, url, snippet.
    """
    # stub: replace with real search integration in Phase X
    return [
        {
            "title": f"Result {i + 1} for '{query}'",
            "url": f"https://example.com/search?q={query}&page={i + 1}",
            "snippet": f"This is a placeholder snippet for result {i + 1} matching '{query}'.",
        }
        for i in range(max_results)
    ]


# ---------------------------------------------------------------------------
# http_get
# ---------------------------------------------------------------------------


@register_tool(
    name="http_get",
    description="Perform an HTTP GET request to the given URL and return the response body as text.",
)
def http_get(url: str) -> str:
    """
    Fetch the content of a URL via HTTP GET.

    Args:
        url: The URL to fetch.

    Returns:
        The response body as a string.
    """
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    return response.text


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


@register_tool(
    name="read_file",
    description="Read the contents of a file at the given path and return it as text.",
)
def read_file(path: str) -> str:
    """
    Read a file from the filesystem.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        The file contents as a UTF-8 string.

    Security note: This is unsandboxed — any path accessible to the process
    can be read.  Path allow-listing / sandboxing is a Phase 7+ concern.
    """
    return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# current_time
# ---------------------------------------------------------------------------


@register_tool(
    name="current_time",
    description=(
        "Return the current date and time in ISO 8601 format for the given "
        "timezone (default UTC)."
    ),
)
def current_time(tz: str = "UTC") -> str:
    """
    Get the current date and time in the specified timezone.

    Args:
        tz: IANA timezone name (e.g. 'UTC', 'America/New_York'). Default is 'UTC'.

    Returns:
        ISO 8601 datetime string (e.g. '2026-05-21T14:30:00+00:00').
    """
    return datetime.now(zoneinfo.ZoneInfo(tz)).isoformat()
