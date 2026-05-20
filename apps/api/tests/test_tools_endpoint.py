"""
Tests for Phase 1B: GET /v1/tools endpoint.

Run with:
    cd apps/api && python3 -m pytest tests/test_tools_endpoint.py -v
"""

from __future__ import annotations

import pytest


def test_get_tools_returns_200(api_client):
    """GET /v1/tools must respond with HTTP 200."""
    response = api_client.get("/v1/tools")
    assert response.status_code == 200


def test_get_tools_returns_list_with_four_items(api_client):
    """GET /v1/tools must return a JSON list with at least 4 items."""
    response = api_client.get("/v1/tools")
    data = response.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert len(data) >= 4, f"Expected at least 4 tools, got {len(data)}"


def test_each_descriptor_has_required_fields(api_client):
    """Every tool descriptor must have name (str), description (str), and input_schema (dict with type: object)."""
    response = api_client.get("/v1/tools")
    data = response.json()
    for item in data:
        assert isinstance(item.get("name"), str), (
            f"'name' must be a str; got {item.get('name')!r}"
        )
        assert isinstance(item.get("description"), str), (
            f"'description' must be a str; got {item.get('description')!r}"
        )
        schema = item.get("input_schema")
        assert isinstance(schema, dict), (
            f"'input_schema' must be a dict; got {schema!r}"
        )
        assert schema.get("type") == "object", (
            f"'input_schema.type' must be 'object'; got {schema.get('type')!r}"
        )


def test_known_tool_present(api_client):
    """web_search must appear in the returned tool list."""
    response = api_client.get("/v1/tools")
    names = {t["name"] for t in response.json()}
    assert "web_search" in names, (
        f"'web_search' not found in tool names: {names}"
    )
