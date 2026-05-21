"""Tests for /v1/agents/{id}/secrets CRUD endpoints."""
import uuid


def _create_agent(api_client) -> str:
    resp = api_client.post("/v1/agents", json={
        "config": {
            "name": f"secret-test-{uuid.uuid4().hex[:6]}",
            "model": "meta/llama-3.1-70b-instruct",
            "instruction": "test",
        }
    })
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def test_list_secrets_empty(api_client):
    agent_id = _create_agent(api_client)
    resp = api_client.get(f"/v1/agents/{agent_id}/secrets")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_secret(api_client):
    agent_id = _create_agent(api_client)
    resp = api_client.post(f"/v1/agents/{agent_id}/secrets", json={
        "service": "telegram", "key_name": "bot_token", "value": "12345:secret",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["service"] == "telegram"
    assert data["key_name"] == "bot_token"
    assert "value" not in data


def test_list_secrets_after_create(api_client):
    agent_id = _create_agent(api_client)
    api_client.post(f"/v1/agents/{agent_id}/secrets", json={
        "service": "telegram", "key_name": "bot_token", "value": "tok"
    })
    resp = api_client.get(f"/v1/agents/{agent_id}/secrets")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_upsert_secret(api_client):
    agent_id = _create_agent(api_client)
    api_client.post(f"/v1/agents/{agent_id}/secrets", json={
        "service": "telegram", "key_name": "bot_token", "value": "v1"
    })
    api_client.post(f"/v1/agents/{agent_id}/secrets", json={
        "service": "telegram", "key_name": "bot_token", "value": "v2"
    })
    resp = api_client.get(f"/v1/agents/{agent_id}/secrets")
    assert len(resp.json()) == 1


def test_delete_secret(api_client):
    agent_id = _create_agent(api_client)
    api_client.post(f"/v1/agents/{agent_id}/secrets", json={
        "service": "slack", "key_name": "webhook_url", "value": "https://hooks.slack.com/..."
    })
    resp = api_client.delete(f"/v1/agents/{agent_id}/secrets/slack/webhook_url")
    assert resp.status_code == 204
    resp2 = api_client.get(f"/v1/agents/{agent_id}/secrets")
    assert resp2.json() == []


def test_secrets_return_404_for_unknown_agent(api_client):
    resp = api_client.get("/v1/agents/nonexistent-id/secrets")
    assert resp.status_code == 404
