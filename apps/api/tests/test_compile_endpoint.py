"""
Tests for Phase 2B: post-validation + SSE /agents/compile endpoint.

Run with:
    cd apps/api && python3 -m pytest tests/test_compile_endpoint.py -v
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_compile_result(config: dict) -> "CompileResult":
    """Build a CompileResult with the given config dict."""
    from agent_runtime.compiler import CompileResult

    return CompileResult(config=config, raw_response=json.dumps(config))


def _mock_compile_prompt(config: dict):
    """Return a coroutine mock that yields a CompileResult with the given config."""
    result = _make_compile_result(config)
    return AsyncMock(return_value=result)


# ---------------------------------------------------------------------------
# 1. Validator: accepts valid config
# ---------------------------------------------------------------------------


def test_compile_validator_accepts_valid_config():
    """validate_agent_config() must not raise for a fully valid config."""
    from agent_runtime.validator import validate_agent_config

    validate_agent_config({
        "name": "x",
        "model": "qwen/qwen3-coder-480b-a35b-instruct",
        "instruction": "do stuff",
        "tools": ["web_search"],
    })
    # If no exception is raised, the test passes


# ---------------------------------------------------------------------------
# 2. Validator: rejects unknown tool
# ---------------------------------------------------------------------------


def test_compile_validator_rejects_unknown_tool():
    """validate_agent_config() must raise CompileValidationError for an unregistered tool."""
    from agent_runtime.validator import CompileValidationError, validate_agent_config

    with pytest.raises(CompileValidationError) as exc_info:
        validate_agent_config({
            "name": "x",
            "model": "qwen/qwen3-coder-480b-a35b-instruct",
            "instruction": "do stuff",
            "tools": ["fake_tool"],
        })

    assert exc_info.value.delta.unknown_tools == ["fake_tool"], (
        f"Expected unknown_tools=['fake_tool'], got {exc_info.value.delta.unknown_tools!r}"
    )


# ---------------------------------------------------------------------------
# 3. Validator: rejects invalid model
# ---------------------------------------------------------------------------


def test_compile_validator_rejects_invalid_model():
    """validate_agent_config() must flag a model not in the allowlist."""
    from agent_runtime.validator import CompileValidationError, validate_agent_config

    with pytest.raises(CompileValidationError) as exc_info:
        validate_agent_config({
            "name": "x",
            "model": "some-bogus-model",
            "instruction": "do stuff",
        })

    assert exc_info.value.delta.invalid_model == "some-bogus-model", (
        f"Expected invalid_model='some-bogus-model', got {exc_info.value.delta.invalid_model!r}"
    )


# ---------------------------------------------------------------------------
# 4. Validator: rejects missing required fields
# ---------------------------------------------------------------------------


def test_compile_validator_rejects_missing_required():
    """validate_agent_config() must list missing required fields in the delta."""
    from agent_runtime.validator import CompileValidationError, validate_agent_config

    with pytest.raises(CompileValidationError) as exc_info:
        validate_agent_config({"model": "gpt-4o-mini"})

    missing = exc_info.value.delta.missing_required
    assert "name" in missing, f"Expected 'name' in missing_required, got {missing!r}"
    assert "instruction" in missing, (
        f"Expected 'instruction' in missing_required, got {missing!r}"
    )


# ---------------------------------------------------------------------------
# 5. Endpoint: streams result on success
# ---------------------------------------------------------------------------


def test_compile_endpoint_streams_result_on_success(api_client, monkeypatch):
    """POST /v1/agents/compile must stream status + result events on a valid config."""
    import api.routers.compile as compile_router_module

    good_config = {
        "name": "weather",
        "model": "qwen/qwen3-coder-480b-a35b-instruct",
        "instruction": "x",
        "tools": ["web_search"],
    }
    monkeypatch.setattr(
        compile_router_module, "compile_prompt", _mock_compile_prompt(good_config)
    )

    response = api_client.post(
        "/v1/agents/compile",
        json={"prompt": "tell me the weather"},
    )

    assert response.status_code == 200
    body = response.text

    assert "event: status" in body, f"Expected 'event: status' in body:\n{body}"
    assert "event: result" in body, f"Expected 'event: result' in body:\n{body}"
    assert "weather" in body, f"Expected config name 'weather' in body:\n{body}"


# ---------------------------------------------------------------------------
# 6. Endpoint: streams error on invalid tool
# ---------------------------------------------------------------------------


def test_compile_endpoint_streams_error_on_invalid_tool(api_client, monkeypatch):
    """POST /v1/agents/compile must stream an error event when the config has an unknown tool."""
    import api.routers.compile as compile_router_module

    bad_config = {
        "name": "bad_agent",
        "model": "qwen/qwen3-coder-480b-a35b-instruct",
        "instruction": "do stuff",
        "tools": ["nonexistent"],
    }
    monkeypatch.setattr(
        compile_router_module, "compile_prompt", _mock_compile_prompt(bad_config)
    )

    response = api_client.post(
        "/v1/agents/compile",
        json={"prompt": "some prompt"},
    )

    assert response.status_code == 200
    body = response.text

    assert "event: error" in body, f"Expected 'event: error' in body:\n{body}"
    assert "unknown_tools" in body, f"Expected 'unknown_tools' in body:\n{body}"
    assert "nonexistent" in body, f"Expected tool name 'nonexistent' in body:\n{body}"


# ---------------------------------------------------------------------------
# 7. Endpoint: streams error on non-JSON LLM response
# ---------------------------------------------------------------------------


def test_compile_endpoint_streams_error_on_non_json_llm(api_client, monkeypatch):
    """POST /v1/agents/compile must stream a compile-stage error when compile_prompt raises ValueError."""
    import api.routers.compile as compile_router_module

    async def _raise_value_error(prompt: str):
        raise ValueError("LLM did not return valid JSON")

    monkeypatch.setattr(compile_router_module, "compile_prompt", _raise_value_error)

    response = api_client.post(
        "/v1/agents/compile",
        json={"prompt": "something"},
    )

    assert response.status_code == 200
    body = response.text

    assert "event: error" in body, f"Expected 'event: error' in body:\n{body}"
    assert '"stage": "compile"' in body or "'stage': 'compile'" in body or "compile" in body, (
        f"Expected compile stage in error body:\n{body}"
    )
