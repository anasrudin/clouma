"""
Tests for Phase 2A: Catalog-driven AgentConfig compiler skeleton.

Run with:
    cd apps/api && python3 -m pytest tests/test_compiler.py -v
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# 1. Tool catalog markdown contains known tools
# ---------------------------------------------------------------------------


def test_build_tool_catalog_markdown_contains_known_tools():
    """_build_tool_catalog_markdown() must include all 4 builtin tool names
    and the markdown table header."""
    from agent_runtime.compiler import _build_tool_catalog_markdown

    catalog = _build_tool_catalog_markdown()

    assert "| name |" in catalog, f"Table header not found in catalog:\n{catalog}"
    for tool_name in ("web_search", "http_get", "read_file", "current_time"):
        assert tool_name in catalog, (
            f"Expected tool '{tool_name}' in catalog markdown, not found:\n{catalog}"
        )


# ---------------------------------------------------------------------------
# 2. AgentConfig schema loads and has expected structure
# ---------------------------------------------------------------------------


def test_agent_config_schema_loads():
    """AGENT_CONFIG_SCHEMA must be a dict with the ADK oneOf structure.

    The real ADK schema (not the fallback) is a oneOf schema where
    LlmAgentConfig has properties including name, model, instruction.
    We check:
      - top-level type is dict
      - oneOf or properties is present
      - LlmAgentConfig (in $defs) has 'name' and 'instruction' in required
    """
    from agent_runtime.compiler import AGENT_CONFIG_SCHEMA

    assert isinstance(AGENT_CONFIG_SCHEMA, dict), (
        f"AGENT_CONFIG_SCHEMA must be a dict, got {type(AGENT_CONFIG_SCHEMA)}"
    )

    # The real ADK schema uses oneOf at the top level
    assert "oneOf" in AGENT_CONFIG_SCHEMA or "properties" in AGENT_CONFIG_SCHEMA, (
        "Schema must have 'oneOf' or 'properties' at top level"
    )

    # When the real ADK schema is present, $defs.LlmAgentConfig has required fields
    defs = AGENT_CONFIG_SCHEMA.get("$defs", {})
    if defs and "LlmAgentConfig" in defs:
        llm_cfg = defs["LlmAgentConfig"]
        required = llm_cfg.get("required", [])
        assert "name" in required, (
            f"LlmAgentConfig.required must include 'name'; got {required}"
        )
        assert "instruction" in required, (
            f"LlmAgentConfig.required must include 'instruction'; got {required}"
        )
    else:
        # Fallback minimal schema: check properties key
        assert "properties" in AGENT_CONFIG_SCHEMA, (
            "Fallback schema must have 'properties'"
        )
        props = AGENT_CONFIG_SCHEMA["properties"]
        for field in ("name", "model", "instruction"):
            assert field in props, (
                f"Fallback schema properties must include '{field}'; got {list(props.keys())}"
            )


# ---------------------------------------------------------------------------
# 3. compile_prompt returns correct result with mocked LLM
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compile_prompt_with_mocked_llm(monkeypatch):
    """compile_prompt() must parse LLM JSON output into a CompileResult.

    The mock returns a valid AgentConfig JSON string; we assert the parsed
    result has the expected name and tools without calling the real LLM.
    """
    from agent_runtime import compiler as compiler_module
    from agent_runtime.compiler import compile_prompt

    fake_content = json.dumps({
        "name": "weather_agent",
        "model": "qwen/qwen3-coder-480b-a35b-instruct",
        "instruction": "You report weather",
        "tools": ["http_get"],
    })

    # Build the mock response chain:
    # client.chat.completions.create(...) -> mock_response
    # mock_response.choices[0].message.content -> fake_content
    mock_message = MagicMock()
    mock_message.content = fake_content

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_create = AsyncMock(return_value=mock_response)

    mock_completions = MagicMock()
    mock_completions.create = mock_create

    mock_chat = MagicMock()
    mock_chat.completions = mock_completions

    mock_client = MagicMock()
    mock_client.chat = mock_chat

    monkeypatch.setattr(compiler_module, "_get_client", lambda: mock_client)

    result = await compile_prompt("monitor weather in jakarta")

    assert result.config["name"] == "weather_agent", (
        f"Expected name='weather_agent', got {result.config.get('name')!r}"
    )
    assert "http_get" in result.config["tools"], (
        f"Expected 'http_get' in tools, got {result.config.get('tools')}"
    )
    assert result.raw_response == fake_content, (
        "raw_response must match the original LLM output string"
    )
