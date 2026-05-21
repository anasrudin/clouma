"""Skill registry for Clouma agent runtime.

A skill is a pre-built LlmAgent (sub-agent) with its own tools and instruction.
At runner build time, each skill is wrapped as a google.adk.tools.AgentTool
and passed to the parent LlmAgent so it can delegate tasks naturally.

Skills are registered via _register_skill() and stored in SKILL_REGISTRY.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillEntry:
    """Immutable record for a registered skill."""

    name: str
    description: str
    instruction: str
    tool_names: tuple[str, ...]


SKILL_REGISTRY: dict[str, SkillEntry] = {}


def _register_skill(
    name: str,
    description: str,
    instruction: str,
    tool_names: tuple[str, ...],
) -> None:
    """Register a predefined skill. Raises ValueError on duplicate name."""
    if name in SKILL_REGISTRY:
        raise ValueError(f"Skill '{name}' is already registered.")
    SKILL_REGISTRY[name] = SkillEntry(
        name=name,
        description=description,
        instruction=instruction,
        tool_names=tool_names,
    )


# Auto-register builtin skills on import
from . import catalog as _catalog  # noqa: E402, F401
