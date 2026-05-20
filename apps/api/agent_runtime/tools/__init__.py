"""
Tool registry for Clouma agent runtime.

Tools are registered via the @register_tool decorator, which:
  - Introspects the function signature and type hints to build a JSON Schema
  - Wraps the function as a google.adk.tools.FunctionTool (if ADK is available)
  - Stores a ToolEntry in TOOL_REGISTRY keyed by tool name

Usage:
    from agent_runtime.tools import register_tool, TOOL_REGISTRY
"""

from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import create_model

# ---------------------------------------------------------------------------
# Optional ADK import — registry works even if google-adk isn't installed
# ---------------------------------------------------------------------------
try:
    from google.adk.tools import FunctionTool as _FunctionTool  # type: ignore

    _ADK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FunctionTool = None  # type: ignore
    _ADK_AVAILABLE = False


# ---------------------------------------------------------------------------
# ToolEntry dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolEntry:
    """Immutable record for a registered tool."""

    name: str
    description: str
    input_schema: dict  # JSON Schema object with "type": "object" + "properties"
    fn: Callable[..., Any]  # underlying callable
    adk_tool: Any  # FunctionTool instance, or None if ADK not installed


# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, ToolEntry] = {}


# ---------------------------------------------------------------------------
# Schema builder
# ---------------------------------------------------------------------------


def _build_input_schema(fn: Callable[..., Any]) -> dict:
    """
    Build a JSON Schema (object) from a function's signature and type hints.

    Parameters without defaults become required; parameters with defaults are
    optional.  Return annotation is excluded from the schema.
    """
    sig = inspect.signature(fn)
    hints = typing.get_type_hints(fn)

    fields: dict[str, Any] = {}
    for param_name, param in sig.parameters.items():
        ann = hints.get(param_name, Any)
        if param.default is inspect.Parameter.empty:
            fields[param_name] = (ann, ...)  # required
        else:
            fields[param_name] = (ann, param.default)  # optional with default

    if not fields:
        # No parameters — return a minimal valid schema
        return {"type": "object", "properties": {}}

    model = create_model(f"{fn.__name__}_input", **fields)
    schema = model.model_json_schema()
    return schema


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def register_tool(name: str, description: str) -> Callable[[Callable], Callable]:
    """
    Decorator that registers a function as a tool in TOOL_REGISTRY.

    Args:
        name: Unique tool identifier.
        description: Human-readable description of what the tool does.

    Raises:
        ValueError: If a tool with the same name is already registered.

    Example::

        @register_tool(name="my_tool", description="Does something useful")
        def my_tool(x: int) -> str:
            return str(x)
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        if name in TOOL_REGISTRY:
            raise ValueError(
                f"Tool '{name}' is already registered. "
                "Each tool name must be unique."
            )

        schema = _build_input_schema(fn)

        # Wrap as ADK FunctionTool when available
        adk_tool: Any = None
        if _ADK_AVAILABLE and _FunctionTool is not None:
            adk_tool = _FunctionTool(func=fn)

        entry = ToolEntry(
            name=name,
            description=description,
            input_schema=schema,
            fn=fn,
            adk_tool=adk_tool,
        )
        TOOL_REGISTRY[name] = entry

        # Return the original function unmodified so callers can still invoke it
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Auto-register builtin tools on import
# ---------------------------------------------------------------------------

from agent_runtime.tools import builtin as _builtin  # noqa: E402, F401
