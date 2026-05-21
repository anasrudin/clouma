# apps/api/routers/agents.py
import uuid
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.agent import Agent
from ..schemas.agent import AgentCreate, AgentOut
from agent_runtime.validator import CompileValidationError, validate_agent_config

router = APIRouter(prefix="/agents", tags=["agents"])

SCHEMA_HEADER = (
    "# yaml-language-server: $schema=https://raw.githubusercontent.com/"
    "google/adk-python/refs/heads/main/src/google/adk/agents/config_schemas/AgentConfig.json\n"
)


def _render_yaml(config: dict) -> str:
    return SCHEMA_HEADER + yaml.safe_dump(config, sort_keys=False, default_flow_style=False)


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)):
    try:
        validate_agent_config(payload.config)
    except CompileValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "delta": {
                    "unknown_tools": exc.delta.unknown_tools,
                    "invalid_model": exc.delta.invalid_model,
                    "missing_required": exc.delta.missing_required,
                },
            },
        )

    name = payload.config.get("name", "")
    description = payload.config.get("description")

    agent = Agent(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        config_json=payload.config,
        yaml_cache=_render_yaml(payload.config),
    )
    db.add(agent)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"agent name '{name}' already exists")
    await db.refresh(agent)

    # Register cron job if agent has a schedule
    cron = payload.config.get("schedule")
    if cron:
        from agent_runtime.scheduler import schedule_agent
        prompt = payload.config.get("schedule_prompt")
        schedule_agent(agent.id, cron, name, prompt) if prompt else schedule_agent(agent.id, cron, name)

    return agent


@router.get("", response_model=list[AgentOut])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return result.scalars().all()


@router.get(
    "/{agent_id}",
    response_model=AgentOut,
    responses={
        200: {
            "content": {"application/yaml": {}, "application/json": {}},
        },
        404: {"description": "Agent not found"},
    },
)
async def get_agent(
    agent_id: str,
    format: str = Query("json", pattern="^(json|yaml)$"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail=f"agent {agent_id} not found")

    if format == "yaml":
        from fastapi.responses import PlainTextResponse

        yaml_text = agent.yaml_cache or _render_yaml(agent.config_json)
        return PlainTextResponse(content=yaml_text, media_type="application/yaml")

    return AgentOut.model_validate(agent)


# ---------------------------------------------------------------------------
# PATCH /agents/{agent_id} — partial config update (Phase 5B)
# ---------------------------------------------------------------------------


class AgentPatch(BaseModel):
    """Partial config update — accept full config dict, validate, replace."""

    config: dict[str, Any]


@router.patch("/{agent_id}", response_model=AgentOut)
async def patch_agent(
    agent_id: str,
    payload: AgentPatch,
    db: AsyncSession = Depends(get_db),
):
    """Replace the stored config for an existing agent after validation."""
    # Fetch first — so a PATCH to nonexistent ID always returns 404, not 422
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail=f"agent {agent_id} not found")

    try:
        validate_agent_config(payload.config)
    except CompileValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "delta": {
                    "unknown_tools": exc.delta.unknown_tools,
                    "invalid_model": exc.delta.invalid_model,
                    "missing_required": exc.delta.missing_required,
                },
            },
        )

    agent.config_json = payload.config
    agent.name = payload.config.get("name", agent.name)
    agent.description = payload.config.get("description")
    agent.yaml_cache = _render_yaml(payload.config)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"agent name '{agent.name}' already exists",
        )
    await db.refresh(agent)

    # Reschedule (or remove) cron job based on updated config
    from agent_runtime.scheduler import schedule_agent, unschedule_agent
    cron = payload.config.get("schedule")
    if cron:
        prompt = payload.config.get("schedule_prompt")
        schedule_agent(agent.id, cron, agent.name, prompt) if prompt else schedule_agent(agent.id, cron, agent.name)
    else:
        unschedule_agent(agent.id)

    return agent


# ---------------------------------------------------------------------------
# DELETE /agents/{agent_id}
# ---------------------------------------------------------------------------


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail=f"agent {agent_id} not found")
    await db.delete(agent)
    await db.commit()

    from agent_runtime.scheduler import unschedule_agent
    unschedule_agent(agent_id)
