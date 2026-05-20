"""
Tests for Phase 6: POST /v1/agents/dry-run endpoint.

Run with:
    cd apps/api && python3 -m pytest tests/test_dry_run.py -v
"""
from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_CONFIG = {
    "name": "test_agent",
    "model": "qwen/qwen3-coder-480b-a35b-instruct",
    "instruction": "You are a helpful assistant.",
    "tools": [],
}


def _make_adk_event(text: str) -> MagicMock:
    """Build a minimal mock ADK event that responds to .model_dump()."""
    evt = MagicMock()
    evt.model_dump.return_value = {
        "id": "evt-123",
        "author": "test_agent",
        "content": {"role": "model", "parts": [{"text": text}]},
        "turn_complete": True,
    }
    return evt


# ---------------------------------------------------------------------------
# 1. Rejects invalid config (unknown tool) → ok=False, no 422
# ---------------------------------------------------------------------------


def test_dry_run_rejects_invalid_config(api_client):
    """POST with unknown tool → 200 with ok=False, error mentions 'unknown tools'."""
    resp = api_client.post(
        "/v1/agents/dry-run",
        json={
            "config": {
                "name": "x",
                "model": "qwen/qwen3-coder-480b-a35b-instruct",
                "instruction": "do stuff",
                "tools": ["fake_tool"],
            }
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["ok"] is False
    assert body["error"] is not None
    assert "unknown tools" in body["error"].lower() or "fake_tool" in body["error"], (
        f"Expected error to mention unknown tools, got: {body['error']!r}"
    )


# ---------------------------------------------------------------------------
# 2. Rejects invalid model → ok=False, error mentions model
# ---------------------------------------------------------------------------


def test_dry_run_rejects_invalid_model(api_client):
    """POST with bogus model → 200 with ok=False, error mentions the model."""
    resp = api_client.post(
        "/v1/agents/dry-run",
        json={
            "config": {
                "name": "x",
                "model": "totally-bogus-model-xyz",
                "instruction": "do stuff",
                "tools": [],
            }
        },
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["ok"] is False
    assert body["error"] is not None
    assert "totally-bogus-model-xyz" in body["error"] or "model" in body["error"].lower(), (
        f"Expected error to mention model, got: {body['error']!r}"
    )


# ---------------------------------------------------------------------------
# 3. With mocked Runner — returns events
# ---------------------------------------------------------------------------


def test_dry_run_with_mocked_runner_returns_events(api_client, monkeypatch):
    """Mock Runner.run_async to yield 2 events → ok=True, events has 2 entries."""
    import api.routers.dry_run as dry_run_module

    evt1 = _make_adk_event("Hello")
    evt2 = _make_adk_event("World")

    async def _fake_run_async(*, user_id, session_id, new_message):
        yield evt1
        yield evt2

    # We need to patch the Runner class that gets imported inside the endpoint function.
    # Patch at the module level where it will be imported.
    mock_runner_instance = MagicMock()
    mock_runner_instance.run_async = _fake_run_async

    mock_runner_cls = MagicMock(return_value=mock_runner_instance)

    # Also mock InMemorySessionService so no real ADK call happens
    mock_session = MagicMock()
    mock_session.id = "sess-dry-123"

    mock_session_svc = MagicMock()
    mock_session_svc.create_session = AsyncMock(return_value=mock_session)

    mock_session_svc_cls = MagicMock(return_value=mock_session_svc)

    with (
        patch("google.adk.runners.Runner", mock_runner_cls),
        patch("google.adk.sessions.in_memory_session_service.InMemorySessionService", mock_session_svc_cls),
    ):
        resp = api_client.post(
            "/v1/agents/dry-run",
            json={"config": VALID_CONFIG},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["ok"] is True, f"Expected ok=True, got: {body}"
    assert len(body["events"]) == 2, (
        f"Expected 2 events, got {len(body['events'])}: {body['events']}"
    )
    assert body["elapsed_ms"] is not None


# ---------------------------------------------------------------------------
# 4. Timeout → ok=False, error contains "Timed out"
# ---------------------------------------------------------------------------


def test_dry_run_timeout_returns_ok_false(api_client, monkeypatch):
    """Mock runner that hangs → timeout fires → ok=False with 'Timed out' in error."""
    import api.routers.dry_run as dry_run_module

    async def _hanging_run_async(*, user_id, session_id, new_message):
        await asyncio.sleep(20)
        # Never actually yields
        return
        yield  # make it an async generator

    mock_runner_instance = MagicMock()
    mock_runner_instance.run_async = _hanging_run_async

    mock_runner_cls = MagicMock(return_value=mock_runner_instance)

    mock_session = MagicMock()
    mock_session.id = "sess-dry-timeout"

    mock_session_svc = MagicMock()
    mock_session_svc.create_session = AsyncMock(return_value=mock_session)

    mock_session_svc_cls = MagicMock(return_value=mock_session_svc)

    # Shorten timeout to 0.5s so the test completes quickly
    monkeypatch.setattr(dry_run_module, "DRY_RUN_TIMEOUT_SECONDS", 0.5)

    with (
        patch("google.adk.runners.Runner", mock_runner_cls),
        patch("google.adk.sessions.in_memory_session_service.InMemorySessionService", mock_session_svc_cls),
    ):
        resp = api_client.post(
            "/v1/agents/dry-run",
            json={"config": VALID_CONFIG},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["ok"] is False, f"Expected ok=False on timeout, got: {body}"
    assert body["error"] is not None
    assert "timed out" in body["error"].lower(), (
        f"Expected 'Timed out' in error, got: {body['error']!r}"
    )


# ---------------------------------------------------------------------------
# 5. E2E — skipped unless CLOUMA_E2E=1
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("CLOUMA_E2E") != "1",
    reason="Requires live LLM; set CLOUMA_E2E=1 to enable",
)
def test_dry_run_returns_events_from_real_invocation(api_client):
    """Actually call the LLM and verify we get at least one event back."""
    resp = api_client.post(
        "/v1/agents/dry-run",
        json={
            "config": {
                "name": "e2e_agent",
                "model": "qwen/qwen3-coder-480b-a35b-instruct",
                "instruction": "You are a helpful assistant.",
                "tools": [],
                "dry_run_sample": "say hello",
            }
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True, f"E2E dry-run failed: {body.get('error')}"
    assert len(body["events"]) > 0, "Expected at least one event from real invocation"
