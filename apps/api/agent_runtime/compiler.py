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

MAX_OUTPUT_TOKENS = 1024


# ---------------------------------------------------------------------------
# Tool catalog builder
# ---------------------------------------------------------------------------


def _sanitize_md_cell(s: str) -> str:
    """Escape characters that would break a markdown table row."""
    return s.replace("|", "\\|").replace("\n", " ").replace("\r", "")


# Tools that require agent credentials. Key = tool name, value = "service:key_name" pairs.
TOOL_CREDENTIALS: dict[str, str] = {
    "telegram_send": "telegram:bot_token",
    "slack_send": "slack:webhook_url",
    "confluence_search": "confluence:api_key,confluence:base_url",
    "confluence_create_page": "confluence:api_key,confluence:base_url",
}


def _build_tool_catalog_markdown() -> str:
    """Render registered tools as a markdown table for the LLM system prompt."""
    if not TOOL_REGISTRY:
        return "(no tools registered)"
    lines = ["| name | description | params | requires |", "|---|---|---|---|"]
    for entry in TOOL_REGISTRY.values():
        name = _sanitize_md_cell(entry.name)
        desc = _sanitize_md_cell(entry.description)
        params = ", ".join(entry.input_schema.get("properties", {}).keys()) or "(none)"
        requires = TOOL_CREDENTIALS.get(entry.name, "-")
        lines.append(f"| `{name}` | {desc} | {params} | {requires} |")
    return "\n".join(lines)


def _build_skill_catalog_markdown() -> str:
    """Render registered skills as a markdown table for the LLM system prompt."""
    from agent_runtime.skills import SKILL_REGISTRY
    if not SKILL_REGISTRY:
        return "(no skills registered)"
    lines = ["| name | description | tools used |", "|---|---|---|"]
    for entry in SKILL_REGISTRY.values():
        name = _sanitize_md_cell(entry.name)
        desc = _sanitize_md_cell(entry.description)
        tools = ", ".join(f"`{t}`" for t in entry.tool_names)
        lines.append(f"| `{name}` | {desc} | {tools} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You compile natural-language requests into ADK AgentConfig JSON.

Available tools (you MUST only reference these names in `tools`):

{catalog}

Available skills — sub-agents you can delegate entire tasks to (reference by name in `skills`):

{skill_catalog}

If a tool has a non-dash value in `requires`, the agent needs those credentials. Include a
`permissions` block listing required services:
  permissions:
    - service: telegram
      keys: [bot_token]

Output requirements:
- Return ONLY a single JSON object (no markdown, no prose).
- Required fields: `name` (lowercase slug, underscores only), `model`, `instruction`.
- Optional: `description`, `tools` (names from tool catalog), `skills` (names from skill catalog), `permissions`.
- Do NOT invent tool or skill names. Pick subsets from the catalogs above or use empty arrays.
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
        ValueError: If the LLM returns malformed JSON.
        RuntimeError: If the LLM output was truncated (finish_reason="length").
        openai.APIError: If the LLM call fails.
    """
    client = _get_client()
    system = SYSTEM_PROMPT_TEMPLATE.format(
        catalog=_build_tool_catalog_markdown(),
        skill_catalog=_build_skill_catalog_markdown(),
        model=settings.llm_model,
    )
    resp = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        # low temperature for deterministic structured output
        temperature=0.2,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    choice = resp.choices[0]
    if choice.finish_reason == "length":
        raise RuntimeError(
            f"LLM output was truncated at max_tokens={MAX_OUTPUT_TOKENS}; "
            "increase the limit or shorten the system prompt."
        )
    raw = choice.message.content or "{}"
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        snippet = raw[:200]
        raise ValueError(
            f"LLM did not return valid JSON. First 200 chars: {snippet!r}. "
            f"Original error: {exc.msg} at position {exc.pos}."
        ) from exc
    # LLMs occasionally omit `model` despite the system prompt. Since the prompt
    # already specifies settings.llm_model, we can safely fill it in.
    if not config.get("model"):
        config["model"] = settings.llm_model
    return CompileResult(config=config, raw_response=raw)
