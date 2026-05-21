# apps/api/agent_runtime/runner_factory.py
"""Factory function to build an ADK Runner for a given agent ID.

Loads agent config from the DB, instantiates an LlmAgent, and wraps it in
a Runner backed by PostgresSessionService.

Design notes:
- validate_agent_config() is called defensively before building; it raises
  CompileValidationError on unknown tools, which means no tool is silently
  dropped.  The caller gets a clear error with the list of bad tool names.
- Tools listed in config["tools"] that do not exist in TOOL_REGISTRY will
  cause validate_agent_config to raise (consistent with Phase 2B/3 behavior).
"""
from __future__ import annotations

import re
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from google.adk.tools import AgentTool

from agent_runtime.session_service import PostgresSessionService
from agent_runtime.skills import SKILL_REGISTRY, SkillEntry
from agent_runtime.tools import TOOL_REGISTRY
from agent_runtime.validator import validate_agent_config
from api.models.agent import Agent


def _build_skill_agent_tool(skill: SkillEntry, model: str) -> AgentTool:
    """Wrap a SkillEntry as an ADK AgentTool for use by a parent agent."""
    skill_tools = [
        TOOL_REGISTRY[t].adk_tool
        for t in skill.tool_names
        if t in TOOL_REGISTRY and TOOL_REGISTRY[t].adk_tool is not None
    ]
    adk_agent = LlmAgent(
        name=skill.name,
        model=model,
        instruction=skill.instruction,
        tools=skill_tools,
    )
    return AgentTool(agent=adk_agent)


async def build_runner(
    agent_id: str,
    db_sessionmaker: async_sessionmaker[AsyncSession],
    app_name: Optional[str] = None,
) -> Runner:
    """Load an Agent from the DB and wrap it in an ADK Runner.

    Parameters
    ----------
    agent_id:
        UUID string of the Agent row.
    db_sessionmaker:
        Async SQLAlchemy sessionmaker bound to the application database.
    app_name:
        Override the application name registered on the Runner.  Defaults to
        the agent's ``name`` field from the DB config.

    Returns
    -------
    Runner
        A fully configured ADK Runner ready for ``run_async`` / ``run_live``.

    Raises
    ------
    ValueError
        If no agent with ``agent_id`` exists in the database.
    CompileValidationError
        If the stored config fails validation (unknown tools, bad model, etc.).
    """
    # 1. Load agent config from DB
    async with db_sessionmaker() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent_row: Optional[Agent] = result.scalar_one_or_none()
        if agent_row is None:
            raise ValueError(
                f"Agent '{agent_id}' not found in the database."
            )
        cfg = dict(agent_row.config_json)

    # 2. Defensive re-validation — config might have been edited out-of-band
    validate_agent_config(cfg)

    # 3. Resolve ADK tools from registry
    #    validate_agent_config already ensured all tool names are known, so no
    #    need to filter here — the list is clean.
    selected_tools = [
        TOOL_REGISTRY[name].adk_tool
        for name in cfg.get("tools", [])
        if name in TOOL_REGISTRY and TOOL_REGISTRY[name].adk_tool is not None
    ]

    # 4. Resolve skills from registry
    selected_skills = [
        _build_skill_agent_tool(SKILL_REGISTRY[name], cfg.get("model", ""))
        for name in cfg.get("skills", [])
        if name in SKILL_REGISTRY
    ]

    # 5. Build LlmAgent
    #    ADK requires agent name to be a valid Python identifier.
    #    Sanitize by replacing non-alphanumeric characters with underscores.
    raw_name: str = cfg["name"]
    sanitized_name = re.sub(r"[^A-Za-z0-9_]", "_", raw_name)
    if not sanitized_name or sanitized_name[0].isdigit():
        sanitized_name = "agent_" + sanitized_name

    resolved_app_name = app_name or raw_name
    adk_agent = LlmAgent(
        name=sanitized_name,
        model=cfg.get("model", ""),
        instruction=cfg.get("instruction", ""),
        description=cfg.get("description", ""),
        tools=selected_tools + selected_skills,
    )

    # 6. Create Postgres-backed session service
    session_service = PostgresSessionService(db_sessionmaker)

    # 7. Wrap in Runner
    runner = Runner(
        agent=adk_agent,
        app_name=resolved_app_name,
        session_service=session_service,
    )

    return runner
