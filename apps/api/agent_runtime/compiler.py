"""Catalog-driven AgentConfig compiler.

Given a natural-language prompt, calls the configured LLM to produce a JSON
AgentConfig that references only tools registered in TOOL_REGISTRY.

Phase 2A skeleton: calls LLM with json_object response_format and returns
parsed dict. Post-validation against the schema is deferred to Phase 2B.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from api.config import settings
from agent_runtime.tools import TOOL_REGISTRY


# ---------------------------------------------------------------------------
# Schema (downloaded from upstream ADK repo — real schema, not fallback)
# Source: https://raw.githubusercontent.com/google/adk-python/refs/heads/main/
#         src/google/adk/agents/config_schemas/AgentConfig.json
# The schema uses oneOf over LlmAgentConfig / LoopAgentConfig / etc.
# For Phase 2A we load it but defer validation to Phase 2B.
# ---------------------------------------------------------------------------

SCHEMA_PATH = Path(__file__).parent / "schemas" / "agent_config.json"
AGENT_CONFIG_SCHEMA: dict[str, Any] = json.loads(SCHEMA_PATH.read_text())


# ---------------------------------------------------------------------------
# Tool catalog builder
# ---------------------------------------------------------------------------


def _build_tool_catalog_markdown() -> str:
    """Render the registered tools as a markdown table for the LLM system prompt."""
    if not TOOL_REGISTRY:
        return "(no tools registered)"
    lines = ["| name | description | params |", "|---|---|---|"]
    for entry in TOOL_REGISTRY.values():
        params = ", ".join(entry.input_schema.get("properties", {}).keys()) or "(none)"
        lines.append(f"| `{entry.name}` | {entry.description} | {params} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You compile natural-language requests into ADK AgentConfig JSON.

Available tools (you MUST only reference these names in `tools`):

{catalog}

Output requirements:
- Return ONLY a single JSON object (no markdown, no prose).
- Required fields: `name` (lowercase slug, underscores allowed), `model` (use the one configured below), `instruction` (system prompt for the agent).
- Optional: `description`, `tools` (array of names from the catalog above).
- Do NOT invent tool names. Pick a subset of the catalog or use an empty array.
- Model to use: `{model}`
"""


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


class CompileResult(BaseModel):
    """Result of compiling a prompt to an AgentConfig dict."""

    config: dict[str, Any] = Field(description="The raw AgentConfig JSON returned by the LLM")
    raw_response: str = Field(description="Original LLM response string for debugging")


# ---------------------------------------------------------------------------
# LLM client factory
# ---------------------------------------------------------------------------


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def compile_prompt(user_prompt: str) -> CompileResult:
    """Compile a user prompt to an AgentConfig dict (not yet validated against schema).

    Phase 2B will add post-validation (tool-name existence, schema compliance).

    Args:
        user_prompt: Natural-language description of what the agent should do.

    Returns:
        CompileResult with the parsed AgentConfig dict and the raw LLM response.

    Raises:
        json.JSONDecodeError: If the LLM returns malformed JSON.
        openai.APIError: If the LLM call fails.
    """
    client = _get_client()
    system = SYSTEM_PROMPT_TEMPLATE.format(
        catalog=_build_tool_catalog_markdown(),
        model=settings.llm_model,
    )
    resp = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=1024,
    )
    raw = resp.choices[0].message.content or "{}"
    config = json.loads(raw)
    return CompileResult(config=config, raw_response=raw)
