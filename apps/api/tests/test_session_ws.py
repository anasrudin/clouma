# apps/api/tests/test_session_ws.py
"""Phase 4B tests: WebSocket endpoint /sessions/{session_id}/ws.

Tests
-----
1. test_ws_streams_runner_events
   Open the WS, send init + one input message, expect 2 ADK events forwarded.

2. test_ws_returns_error_on_missing_agent
   Init with an unknown agent_id → server sends stream_error and exits.

3. test_integration_compile_save_ws_stream
   Chain:
     a. POST /v1/agents/compile  (mocked → returns valid AgentConfig)
     b. POST /v1/agents           (save the agent)
     c. WS /sessions/{sid}/ws    (send init + input, assert event received)

Notes
-----
- FastAPI's TestClient wraps anyio and runs the full ASGI app.  WebSocket
  testing uses client.websocket_connect().
- We mock build_runner (or Runner.run_async) so no real LLM call is made.
- Because TestClient is synchronous, we use monkeypatch on the module-level
  import inside routers/sessions.py.  The trick: patch
  ``api.routers.sessions.build_runner`` (the name as it appears after the
  deferred ``from agent_runtime.runner_factory import build_runner`` inside the
  handler).  Instead, we patch the factory module directly so the import picks
  up the mock.
"""
from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api.main as _api_main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_runner(events: list[dict]) -> MagicMock:
    """Return a MagicMock Runner whose run_async yields the given event dicts."""

    async def _fake_run_async(**kwargs) -> AsyncGenerator:
        from google.adk.events.event import Event
        from google.genai.types import Content, Part

        for ev in events:
            yield Event(
                author=ev.get("author", "model"),
                content=Content(
                    role=ev.get("role", "model"),
                    parts=[Part(text=ev.get("text", ""))],
                ),
            )

    fake_session = MagicMock()
    fake_session.id = "adk-session-fake"

    fake_service = MagicMock()
    fake_service.get_session = AsyncMock(return_value=None)
    fake_service.create_session = AsyncMock(return_value=fake_session)

    runner = MagicMock()
    runner.run_async = _fake_run_async
    runner.session_service = fake_service

    return runner


# ---------------------------------------------------------------------------
# 1. test_ws_streams_runner_events
# ---------------------------------------------------------------------------


def test_ws_streams_runner_events(monkeypatch):
    """Open WS, send init + input, expect 2 ADK events forwarded."""
    fake_runner = _make_fake_runner([
        {"author": "model", "text": "hello"},
        {"author": "model", "text": " world"},
    ])

    async def _fake_build_runner(agent_id, db_sessionmaker, app_name=None):
        return fake_runner

    monkeypatch.setattr(
        "agent_runtime.runner_factory.build_runner", _fake_build_runner
    )
    # Also patch the deferred import path used inside the WS handler
    with patch("agent_runtime.runner_factory.build_runner", _fake_build_runner):
        with TestClient(_api_main.app, raise_server_exceptions=True) as client:
            session_id = str(uuid.uuid4())
            with client.websocket_connect(f"/v1/sessions/{session_id}/ws") as ws:
                # Send init
                ws.send_json({"agent_id": "agent-123", "user_id": "user-1"})
                # Send input
                ws.send_json({"input": "Say hello"})

                received = []
                for _ in range(2):
                    data = ws.receive_json()
                    received.append(data)

    assert len(received) == 2, f"Expected 2 events, got {len(received)}: {received}"
    assert received[0]["author"] == "model"
    assert received[1]["author"] == "model"
    # Verify content round-trip
    parts0 = received[0]["content"]["parts"]
    assert any("hello" in (p.get("text") or "") for p in parts0), (
        f"Expected 'hello' in first event parts, got: {parts0}"
    )


# ---------------------------------------------------------------------------
# 2. test_ws_returns_error_on_missing_agent
# ---------------------------------------------------------------------------


def test_ws_returns_error_on_missing_agent():
    """Init with unknown agent_id → server sends stream_error."""

    with TestClient(_api_main.app, raise_server_exceptions=False) as client:
        session_id = str(uuid.uuid4())
        with client.websocket_connect(f"/v1/sessions/{session_id}/ws") as ws:
            # Send init with an agent_id that does not exist in DB
            ws.send_json({"agent_id": "nonexistent-agent-xyz-9999"})
            data = ws.receive_json()

    assert data.get("type") == "stream_error", (
        f"Expected stream_error, got: {data}"
    )
    assert "error" in data, f"Expected 'error' key in response: {data}"


# ---------------------------------------------------------------------------
# 3. test_ws_missing_agent_id_in_init
# ---------------------------------------------------------------------------


def test_ws_missing_agent_id_in_init():
    """Init message without agent_id → server sends stream_error immediately."""
    with TestClient(_api_main.app, raise_server_exceptions=False) as client:
        session_id = str(uuid.uuid4())
        with client.websocket_connect(f"/v1/sessions/{session_id}/ws") as ws:
            ws.send_json({"user_id": "u1"})  # no agent_id
            data = ws.receive_json()

    assert data.get("type") == "stream_error"


# ---------------------------------------------------------------------------
# 4. E2E: compile → save → run via WS
# ---------------------------------------------------------------------------


def test_integration_compile_save_ws_stream(monkeypatch):
    """Integration test: HTTP compile→save chain is real against the test DB; build_runner is mocked because the real ADK Runner needs a live LLM. Each layer has its own unit tests in test_runner_factory.py and test_session_service.py.

    Chain:
    1. POST /v1/agents/compile  → get config from SSE stream
    2. POST /v1/agents          → save agent, get agent_id
    3. WS  /v1/sessions/{sid}/ws → send init + input, receive 1 ADK event
    """
    import api.routers.compile as compile_mod
    from agent_runtime.compiler import CompileResult

    # --- Mock compile_prompt ---
    good_config = {
        "name": "e2e-test-agent",
        "model": "gemini-flash-latest",
        "instruction": "You are a test agent.",
        "tools": ["web_search"],
    }

    async def _fake_compile(prompt: str) -> CompileResult:
        return CompileResult(config=good_config, raw_response=json.dumps(good_config))

    monkeypatch.setattr(compile_mod, "compile_prompt", _fake_compile)

    # --- Mock build_runner ---
    fake_runner = _make_fake_runner([
        {"author": "model", "text": "E2E response"},
    ])

    async def _fake_build_runner(agent_id, db_sessionmaker, app_name=None):
        return fake_runner

    with patch("agent_runtime.runner_factory.build_runner", _fake_build_runner):
        with TestClient(_api_main.app, raise_server_exceptions=True) as client:

            # Step 1: compile
            compile_resp = client.post(
                "/v1/agents/compile", json={"prompt": "Build me a research agent"}
            )
            assert compile_resp.status_code == 200, f"Compile failed: {compile_resp.text}"

            # Extract config from SSE result event
            config_from_compile: dict | None = None
            for line in compile_resp.text.splitlines():
                if line.startswith("data:"):
                    try:
                        payload = json.loads(line[5:].strip())
                        if "config" in payload:
                            config_from_compile = payload["config"]
                            break
                    except (json.JSONDecodeError, KeyError):
                        continue
            assert config_from_compile is not None, (
                f"Could not extract config from compile SSE stream:\n{compile_resp.text}"
            )

            # Step 2: save agent
            save_resp = client.post("/v1/agents", json={"config": config_from_compile})
            assert save_resp.status_code == 201, f"Save agent failed: {save_resp.text}"
            agent_id = save_resp.json()["id"]
            assert agent_id, "Expected non-empty agent_id"

            # Step 3: WS stream
            session_id = str(uuid.uuid4())
            with client.websocket_connect(f"/v1/sessions/{session_id}/ws") as ws:
                ws.send_json({"agent_id": agent_id, "user_id": "e2e-user"})
                ws.send_json({"input": "Hello, agent!"})
                event = ws.receive_json()

    assert event.get("author") == "model", (
        f"Expected author='model' in event, got: {event}"
    )
    text_parts = event.get("content", {}).get("parts", [])
    assert any("E2E response" in (p.get("text") or "") for p in text_parts), (
        f"Expected 'E2E response' in event parts, got: {text_parts}"
    )
