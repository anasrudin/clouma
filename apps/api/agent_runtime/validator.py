"""Post-LLM validation for AgentConfig dicts.

Phase 2B: ensures tool names exist in the registry and the model is allowlisted.
Raises CompileValidationError with a structured `delta` describing what to fix.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_runtime.tools import TOOL_REGISTRY


# Phase 2B allowlist. Expand as needed; matches the plan.
MODEL_ALLOWLIST: frozenset[str] = frozenset({
    "gemini-flash-latest",
    "gpt-4o-mini",
    "qwen/qwen3-coder-480b-a35b-instruct",
})


@dataclass
class ValidationDelta:
    """Structured description of what's wrong with a compile result."""
    unknown_tools: list[str] = field(default_factory=list)
    invalid_model: str | None = None
    missing_required: list[str] = field(default_factory=list)


class CompileValidationError(Exception):
    """Raised when an AgentConfig dict fails post-LLM validation."""
    def __init__(self, message: str, delta: ValidationDelta):
        super().__init__(message)
        self.delta = delta


# Minimal required-field check (the full ADK schema is too lenient — LlmAgentConfig
# requires name + instruction; we also require model for our runtime).
REQUIRED_FIELDS: tuple[str, ...] = ("name", "model", "instruction")


def validate_agent_config(cfg: dict[str, Any]) -> None:
    """Validate an AgentConfig dict against tool registry, model allowlist, and required fields.

    Raises CompileValidationError if any check fails. Otherwise returns None.

    Notes:
    - Empty-string tool names in the ``tools`` list are silently skipped; they
      are not flagged as unknown tools. Empty-string ``model`` is only flagged
      via ``missing_required``, not ``invalid_model``.
    """
    delta = ValidationDelta()

    # 1. Required fields
    for field_name in REQUIRED_FIELDS:
        if field_name not in cfg or cfg.get(field_name) in (None, ""):
            delta.missing_required.append(field_name)

    # 2. Model allowlist (only if model is a non-empty string — required-field check
    #    already covers missing/None/""; empty string is only flagged as missing, not invalid)
    model = cfg.get("model")
    if isinstance(model, str) and model and model not in MODEL_ALLOWLIST:
        delta.invalid_model = model

    # 3. Tool names (blank/empty strings are skipped silently)
    tools = cfg.get("tools", [])
    if isinstance(tools, list):
        for tool_name in tools:
            if isinstance(tool_name, str) and tool_name and tool_name not in TOOL_REGISTRY:
                delta.unknown_tools.append(tool_name)

    if delta.unknown_tools or delta.invalid_model or delta.missing_required:
        parts = []
        if delta.missing_required:
            parts.append(f"missing required: {delta.missing_required}")
        if delta.invalid_model:
            parts.append(f"invalid model: {delta.invalid_model!r}")
        if delta.unknown_tools:
            parts.append(f"unknown tools: {delta.unknown_tools}")
        raise CompileValidationError(
            "AgentConfig failed validation: " + "; ".join(parts), delta
        )
