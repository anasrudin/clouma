"""SSE endpoint that streams the compile-prompt-to-AgentConfig pipeline."""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_runtime.compiler import compile_prompt
from agent_runtime.validator import (
    CompileValidationError,
    validate_agent_config,
)


router = APIRouter(prefix="/agents", tags=["compile"])


class CompileRequest(BaseModel):
    prompt: str


def _sse(event: str, data: dict | str) -> str:
    """Encode an SSE event frame."""
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


async def _compile_stream(prompt: str) -> AsyncIterator[str]:
    yield _sse("status", {"phase": "discovering_tools"})
    # No-op for now; tool catalog is built inside compile_prompt. Phase placeholder
    # so the UI can render a step indicator.

    yield _sse("status", {"phase": "calling_llm"})
    try:
        result = await compile_prompt(prompt)
    except (ValueError, RuntimeError) as exc:
        # LLM/JSON errors from compile_prompt (non-JSON, truncation)
        yield _sse("error", {"stage": "compile", "message": str(exc)})
        return

    yield _sse("status", {"phase": "validating"})
    try:
        validate_agent_config(result.config)
    except CompileValidationError as exc:
        yield _sse(
            "error",
            {
                "stage": "validate",
                "message": str(exc),
                "delta": {
                    "unknown_tools": exc.delta.unknown_tools,
                    "invalid_model": exc.delta.invalid_model,
                    "missing_required": exc.delta.missing_required,
                },
            },
        )
        return

    yield _sse("result", {"config": result.config})


@router.post("/compile")
async def compile_agent(req: CompileRequest) -> StreamingResponse:
    """Stream the compilation pipeline as Server-Sent Events.

    Events:
      - status: {phase: "discovering_tools" | "calling_llm" | "validating"}
      - result: {config: AgentConfig JSON}
      - error: {stage: "compile" | "validate", message: str, delta?: ...}
    """
    return StreamingResponse(
        _compile_stream(req.prompt),
        media_type="text/event-stream",
    )
