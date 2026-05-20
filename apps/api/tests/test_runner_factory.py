# apps/api/tests/test_runner_factory.py
"""Tests for build_runner() (Phase 4A).

Uses SQLite in-memory for the DB layer.
ADK Runner + LlmAgent instantiation does NOT require a live LLM client —
instantiation only, no run_async calls are made.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from api.database import Base
from api.models.agent import Agent
from api.models.session_event import SessionRow, EventRow  # register with Base
from api.agent_runtime.runner_factory import build_runner
from agent_runtime.validator import CompileValidationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def db_sessionmaker():
    """In-memory SQLite sessionmaker with full schema."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    yield sm
    await engine.dispose()


async def _insert_agent(
    sm: async_sessionmaker,
    agent_id: str,
    config: dict,
) -> None:
    """Helper: insert an Agent row into the test DB."""
    row = Agent(
        id=agent_id,
        name=config.get("name", "test_agent"),
        description=config.get("description", ""),
        config_json=config,
    )
    async with sm() as db:
        db.add(row)
        await db.commit()


# ---------------------------------------------------------------------------
# Test 1: build_runner loads config and creates a Runner
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_runner_loads_config_from_db(db_sessionmaker):
    """build_runner should produce a Runner whose agent name matches config."""
    agent_id = str(uuid.uuid4())
    cfg = {
        "name": "my_agent",
        "model": "gemini-flash-latest",
        "instruction": "Be helpful.",
        "tools": ["web_search"],
    }
    await _insert_agent(db_sessionmaker, agent_id, cfg)

    runner = await build_runner(agent_id, db_sessionmaker)

    assert runner is not None
    # Agent name is sanitized to valid Python identifier; "my_agent" is unchanged
    assert runner.agent.name == "my_agent"
    assert runner.app_name == "my_agent"


# ---------------------------------------------------------------------------
# Test 2: build_runner raises ValueError for unknown agent ID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_runner_raises_on_missing_agent(db_sessionmaker):
    """build_runner should raise ValueError if agent_id is not in the DB."""
    with pytest.raises(ValueError, match="not found"):
        await build_runner("nonexistent-id-9999", db_sessionmaker)


# ---------------------------------------------------------------------------
# Test 3: build_runner raises on unknown tools (validation-first strategy)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_runner_raises_on_unknown_tools(db_sessionmaker):
    """build_runner rejects configs referencing tools not in TOOL_REGISTRY.

    Design decision: we call validate_agent_config() defensively before
    building, so an unknown tool name raises CompileValidationError — the same
    error raised by the compile endpoint.  Nothing is silently dropped.
    """
    agent_id = str(uuid.uuid4())
    cfg = {
        "name": "bad_tools_agent",
        "model": "gemini-flash-latest",
        "instruction": "Do stuff.",
        "tools": ["web_search", "totally_fake_tool"],
    }
    await _insert_agent(db_sessionmaker, agent_id, cfg)

    with pytest.raises(CompileValidationError) as exc_info:
        await build_runner(agent_id, db_sessionmaker)

    assert "totally_fake_tool" in exc_info.value.delta.unknown_tools


# ---------------------------------------------------------------------------
# Test 4: build_runner passes only registered tools to LlmAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_runner_passes_registered_tools(db_sessionmaker):
    """Runner.agent.tools contains the resolved FunctionTool instances."""
    agent_id = str(uuid.uuid4())
    cfg = {
        "name": "tool_agent",
        "model": "gemini-flash-latest",
        "instruction": "Use tools.",
        "tools": ["web_search", "current_time"],
    }
    await _insert_agent(db_sessionmaker, agent_id, cfg)

    runner = await build_runner(agent_id, db_sessionmaker)

    # LlmAgent stores tools; check we got 2
    assert len(runner.agent.tools) == 2
