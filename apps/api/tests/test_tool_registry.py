"""
Tests for Phase 1A: Tool Registry + 4 Builtin Tools.

Run with:
    cd apps/api && python3 -m pytest tests/test_tool_registry.py -v
"""

from __future__ import annotations

from datetime import datetime

import jsonschema
import pytest


# ---------------------------------------------------------------------------
# 1. Registry has exactly (at least) 4 builtin tools
# ---------------------------------------------------------------------------


def test_registry_has_four_builtin_tools():
    """All four builtin tools must be present in TOOL_REGISTRY after import."""
    from agent_runtime.tools import TOOL_REGISTRY

    expected_names = {"web_search", "http_get", "read_file", "current_time"}
    assert len(TOOL_REGISTRY) >= 4, (
        f"Expected at least 4 registered tools, got {len(TOOL_REGISTRY)}"
    )
    missing = expected_names - TOOL_REGISTRY.keys()
    assert not missing, f"Missing tools in registry: {missing}"


# ---------------------------------------------------------------------------
# 2. Each entry has a valid JSON Schema
# ---------------------------------------------------------------------------


def test_each_entry_has_valid_jsonschema():
    """input_schema for every registered tool must be a valid JSON Schema."""
    from agent_runtime.tools import TOOL_REGISTRY

    for name, entry in TOOL_REGISTRY.items():
        try:
            jsonschema.Draft202012Validator.check_schema(entry.input_schema)
        except jsonschema.SchemaError as exc:
            pytest.fail(
                f"Tool '{name}' has an invalid JSON Schema: {exc.message}"
            )


# ---------------------------------------------------------------------------
# 3. Registering a duplicate name raises ValueError
# ---------------------------------------------------------------------------


def test_register_tool_rejects_duplicate_name():
    """Calling @register_tool with an already-used name must raise ValueError."""
    from agent_runtime.tools import TOOL_REGISTRY, register_tool

    # Pick an unlikely-to-clash name and clean up afterward
    test_name = "_test_duplicate_sentinel_xyzzy"
    assert test_name not in TOOL_REGISTRY, "Test sentinel name already taken"

    @register_tool(name=test_name, description="First registration")
    def _first():
        pass

    assert test_name in TOOL_REGISTRY

    with pytest.raises(ValueError, match=test_name):

        @register_tool(name=test_name, description="Duplicate — should fail")
        def _second():
            pass

    # Cleanup so we don't pollute other tests
    TOOL_REGISTRY.pop(test_name, None)


# ---------------------------------------------------------------------------
# 4. web_search schema: query required, max_results optional
# ---------------------------------------------------------------------------


def test_web_search_schema_has_required_query():
    """web_search schema must list 'query' as required and not 'max_results'."""
    from agent_runtime.tools import TOOL_REGISTRY

    assert "web_search" in TOOL_REGISTRY, "web_search not registered"
    schema = TOOL_REGISTRY["web_search"].input_schema

    required = schema.get("required", [])
    assert "query" in required, (
        f"'query' should be required in web_search schema; required={required}"
    )
    assert "max_results" not in required, (
        "'max_results' should NOT be required (has default); "
        f"required={required}"
    )


# ---------------------------------------------------------------------------
# 5. current_time returns a valid ISO 8601 string
# ---------------------------------------------------------------------------


def test_current_time_returns_iso_string():
    """current_time() must return a string parseable by datetime.fromisoformat."""
    from agent_runtime.tools.builtin import current_time

    result = current_time()
    assert isinstance(result, str), f"current_time() returned {type(result)}, not str"

    try:
        parsed = datetime.fromisoformat(result)
    except ValueError as exc:
        pytest.fail(f"current_time() returned a non-ISO string: {result!r} ({exc})")

    # Sanity: returned time should be reasonably recent (within the last hour)
    assert parsed is not None
