"""
Tests for Phase 3: AgentConfig persistence with json/yaml endpoints.

Uses an in-memory SQLite database (via aiosqlite) so Postgres is not required.
The conftest.py already sets DATABASE_URL=sqlite+aiosqlite:///:memory: and
creates tables via create_tables() during app lifespan.

Run with:
    cd apps/api && python3 -m pytest tests/test_agents_crud.py -v
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Shared valid config for reuse across tests
# ---------------------------------------------------------------------------

VALID_CONFIG = {
    "name": "test-agent-crud",
    "model": "gemini-flash-latest",
    "instruction": "You are a helpful assistant.",
    "tools": ["web_search"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_name(base: str, suffix: str) -> str:
    """Return a unique agent name to avoid 409 conflicts between tests."""
    return f"{base}-{suffix}"


# ---------------------------------------------------------------------------
# 1. test_create_agent_with_valid_config
# ---------------------------------------------------------------------------


def test_create_agent_with_valid_config(api_client):
    """POST /v1/agents with a valid AgentConfig returns 201 with id and config_json."""
    config = {
        "name": "valid-agent",
        "model": "gemini-flash-latest",
        "instruction": "Help users with questions.",
        "tools": ["web_search"],
    }
    response = api_client.post("/v1/agents", json={"config": config})

    assert response.status_code == 201, response.text
    body = response.json()
    assert "id" in body, f"Expected 'id' in response, got: {body}"
    assert body["config_json"] == config, f"config_json mismatch: {body['config_json']!r}"
    assert body["name"] == config["name"]


# ---------------------------------------------------------------------------
# 2. test_create_agent_rejects_invalid_tool
# ---------------------------------------------------------------------------


def test_create_agent_rejects_invalid_tool(api_client):
    """POST /v1/agents with an unknown tool returns 422 with delta.unknown_tools."""
    config = {
        "name": "bad-tool-agent",
        "model": "gemini-flash-latest",
        "instruction": "Do something.",
        "tools": ["fake_tool"],
    }
    response = api_client.post("/v1/agents", json={"config": config})

    assert response.status_code == 422, response.text
    body = response.json()
    detail = body.get("detail", {})
    assert "delta" in detail, f"Expected 'delta' in detail, got: {detail}"
    assert "fake_tool" in detail["delta"]["unknown_tools"], (
        f"Expected 'fake_tool' in unknown_tools, got: {detail['delta']['unknown_tools']!r}"
    )


# ---------------------------------------------------------------------------
# 3. test_create_agent_rejects_invalid_model
# ---------------------------------------------------------------------------


def test_create_agent_rejects_invalid_model(api_client):
    """POST /v1/agents with a model not in the allowlist returns 422 with delta.invalid_model."""
    config = {
        "name": "bad-model-agent",
        "model": "bogus-model-xyz",
        "instruction": "Do something.",
    }
    response = api_client.post("/v1/agents", json={"config": config})

    assert response.status_code == 422, response.text
    body = response.json()
    detail = body.get("detail", {})
    assert "delta" in detail, f"Expected 'delta' in detail, got: {detail}"
    assert detail["delta"]["invalid_model"] == "bogus-model-xyz", (
        f"Expected invalid_model='bogus-model-xyz', got: {detail['delta']['invalid_model']!r}"
    )


# ---------------------------------------------------------------------------
# 4. test_get_agent_json
# ---------------------------------------------------------------------------


def test_get_agent_json(api_client):
    """GET /v1/agents/{id} returns 200 with config_json matching what was POSTed."""
    config = {
        "name": "get-json-agent",
        "model": "gpt-4o-mini",
        "instruction": "Answer questions briefly.",
    }
    create_resp = api_client.post("/v1/agents", json={"config": config})
    assert create_resp.status_code == 201, create_resp.text
    agent_id = create_resp.json()["id"]

    get_resp = api_client.get(f"/v1/agents/{agent_id}")
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert body["config_json"] == config, f"config_json mismatch: {body['config_json']!r}"
    assert body["id"] == agent_id


# ---------------------------------------------------------------------------
# 5. test_get_agent_yaml
# ---------------------------------------------------------------------------


def test_get_agent_yaml(api_client):
    """GET /v1/agents/{id}?format=yaml returns YAML with the correct header."""
    config = {
        "name": "get-yaml-agent",
        "model": "gpt-4o-mini",
        "instruction": "Be concise.",
    }
    create_resp = api_client.post("/v1/agents", json={"config": config})
    assert create_resp.status_code == 201, create_resp.text
    agent_id = create_resp.json()["id"]

    yaml_resp = api_client.get(f"/v1/agents/{agent_id}", params={"format": "yaml"})
    assert yaml_resp.status_code == 200, yaml_resp.text

    content_type = yaml_resp.headers.get("content-type", "")
    assert "yaml" in content_type, f"Expected application/yaml content-type, got: {content_type}"

    text = yaml_resp.text
    assert text.startswith("# yaml-language-server:"), (
        f"Expected YAML header at start, got: {text[:80]!r}"
    )
    assert "name:" in text, f"Expected 'name:' in YAML body, got: {text}"
    assert "get-yaml-agent" in text, f"Expected agent name in YAML, got: {text}"


# ---------------------------------------------------------------------------
# 6. test_get_agent_not_found
# ---------------------------------------------------------------------------


def test_get_agent_not_found(api_client):
    """GET /v1/agents/nonexistent-uuid returns 404."""
    response = api_client.get("/v1/agents/nonexistent-uuid-does-not-exist")
    assert response.status_code == 404, response.text


# ---------------------------------------------------------------------------
# 7. test_list_agents_empty (uses separate client with fresh DB)
# ---------------------------------------------------------------------------


def test_list_agents_returns_list(api_client):
    """GET /v1/agents returns 200 with a JSON list (may be non-empty due to shared session DB)."""
    response = api_client.get("/v1/agents")
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, list), f"Expected list, got: {type(body)}"


# ---------------------------------------------------------------------------
# 8. test_create_duplicate_name_returns_409
# ---------------------------------------------------------------------------


def test_create_duplicate_name_returns_409(api_client):
    """Creating two agents with the same name returns 409 on the second attempt."""
    config = {
        "name": "duplicate-agent-name",
        "model": "gemini-flash-latest",
        "instruction": "I will be duplicated.",
    }
    first = api_client.post("/v1/agents", json={"config": config})
    assert first.status_code == 201, f"First create failed: {first.text}"

    second = api_client.post("/v1/agents", json={"config": config})
    assert second.status_code == 409, (
        f"Expected 409 on duplicate name, got {second.status_code}: {second.text}"
    )
