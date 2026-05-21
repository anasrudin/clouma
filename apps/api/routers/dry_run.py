"""Dry-run endpoint: build an in-memory ADK Runner from an AgentConfig dict
(no DB persist), execute one sample turn, return events + status.
"""
import asyncio
import re
import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from agent_runtime.model_resolver import resolve_model
from agent_runtime.tools import TOOL_REGISTRY
from agent_runtime.validator import validate_agent_config, CompileValidationError
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import Content, Part

router = APIRouter(prefix="/agents", tags=["dry-run"])

DRY_RUN_TIMEOUT_SECONDS = 10.0
DEFAULT_SAMPLE_INPUT = "say hello"


class DryRunRequest(BaseModel):
    config: dict[str, Any]
    sample_input: str | None = None


class DryRunResponse(BaseModel):
    ok: bool
    events: list[dict[str, Any]]
    error: str | None = None
    elapsed_ms: int | None = None


@router.post("/dry-run", response_model=DryRunResponse)
async def dry_run_agent(req: DryRunRequest) -> DryRunResponse:
    # 1. Validate config before doing anything expensive
    try:
        validate_agent_config(req.config)
    except CompileValidationError as exc:
        return DryRunResponse(ok=False, events=[], error=str(exc))

    # 2. Build in-memory Runner
    cfg = req.config
    # Sanitize name for ADK (same regex used in runner_factory)
    safe_name = re.sub(r"[^A-Za-z0-9_]", "_", cfg["name"]) or "dry_run_agent"
    if safe_name and safe_name[0].isdigit():
        safe_name = "agent_" + safe_name

    selected_tools = [
        TOOL_REGISTRY[name].adk_tool
        for name in cfg.get("tools", [])
        if name in TOOL_REGISTRY and TOOL_REGISTRY[name].adk_tool is not None
    ]

    adk_agent = LlmAgent(
        name=safe_name,
        model=resolve_model(cfg["model"]),
        instruction=cfg["instruction"],
        description=cfg.get("description", ""),
        tools=selected_tools,
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=adk_agent,
        app_name="clouma-dry-run",
        session_service=session_service,
    )

    # 3. Create an in-memory session
    user_id = "dry-run-user"
    session = await session_service.create_session(
        app_name="clouma-dry-run", user_id=user_id,
    )

    sample = req.sample_input or cfg.get("dry_run_sample") or DEFAULT_SAMPLE_INPUT
    new_message = Content(role="user", parts=[Part(text=sample)])

    events: list[dict[str, Any]] = []
    start = time.monotonic()

    try:
        async def consume() -> None:
            async for event in runner.run_async(
                user_id=user_id, session_id=session.id, new_message=new_message,
            ):
                events.append(event.model_dump(mode="json"))

        await asyncio.wait_for(consume(), timeout=DRY_RUN_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        elapsed = int((time.monotonic() - start) * 1000)
        return DryRunResponse(
            ok=False,
            events=events,
            error=f"Timed out after {DRY_RUN_TIMEOUT_SECONDS}s (collected {len(events)} events)",
            elapsed_ms=elapsed,
        )
    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        return DryRunResponse(
            ok=False,
            events=events,
            error=f"{type(exc).__name__}: {exc}",
            elapsed_ms=elapsed,
        )

    elapsed = int((time.monotonic() - start) * 1000)
    return DryRunResponse(ok=True, events=events, elapsed_ms=elapsed)
