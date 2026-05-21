# apps/api/routers/sessions.py
"""Session management routes.

Routes
------
POST   /sessions               — create a legacy Session row (keeps UI compatibility)
GET    /sessions               — list Session rows
WS     /sessions/{id}/ws       — ADK Runner WebSocket stream (Phase 4B, replaces /stream)

The old /sessions/{id}/stream WebSocket route is REMOVED. The new /ws endpoint
forwards real ADK Runner events yielded by runner.run_async().

Decision on the legacy `sessions` table
----------------------------------------
The `sessions` table (models/session.py) is KEPT for now.  It drives the
"Start session" button in the UI and stores agent_id / status for the sessions
list view.  The ADK session (adk_sessions / adk_session_events) is a separate
concern — it holds actual event history.  We do NOT drop the legacy table;
instead we use both in parallel until the UI migrates fully.
"""
from __future__ import annotations

import asyncio
import uuid

WS_INPUT_TIMEOUT = 300

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db, AsyncSessionLocal
from ..models.session import Session
from ..models.agent import Agent
from ..schemas.session import SessionCreate, SessionOut

router = APIRouter()


# ---------------------------------------------------------------------------
# Legacy REST endpoints (kept for UI compatibility)
# ---------------------------------------------------------------------------


@router.post("/sessions", response_model=SessionOut)
async def create_session(req: SessionCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == req.agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    session = Session(agent_id=req.agent_id, status="running")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).order_by(Session.created_at.desc()))
    return result.scalars().all()


@router.post("/sessions/{session_id}/terminate", status_code=200)
async def terminate_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Signal a running session to stop after its current event.

    Sets status to 'terminated' in the DB. The WebSocket handler checks this
    flag cooperatively — it will stop streaming after the next event completes.
    """
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "terminated"
    await db.commit()
    return {"status": "terminated", "session_id": session_id}


# ---------------------------------------------------------------------------
# WebSocket endpoint: ADK Runner stream
# ---------------------------------------------------------------------------


@router.websocket("/sessions/{session_id}/ws")
async def session_ws(websocket: WebSocket, session_id: str):
    """Stream ADK Runner events for a session.

    Protocol
    --------
    1.  Client connects.
    2.  Client sends an *init* message::

            {"agent_id": "...", "user_id": "...", "app_name": "..."}

        ``user_id`` and ``app_name`` are optional (defaults: "default-user", "clouma").

    3.  Server builds an ADK Runner from the DB config, creates/fetches the
        ADK session, then waits for user messages.

    4.  Client sends one or more *input* messages::

            {"input": "user text here"}

    5.  For each input the server calls ``runner.run_async()`` and forwards
        every yielded ``Event`` as JSON over the WebSocket.

    6.  On disconnect the handler exits cleanly.

    Error handling
    --------------
    Any exception during runner setup or event streaming is forwarded to the
    client as ``{"type": "stream_error", "error": "<message>"}`` before closing.
    """
    await websocket.accept()
    try:
        # ----------------------------------------------------------------
        # Step 1: receive init message
        # ----------------------------------------------------------------
        init = await websocket.receive_json()
        agent_id: str = init.get("agent_id", "")
        if not agent_id:
            await websocket.send_json(
                {"type": "stream_error", "error": "init message must include 'agent_id'"}
            )
            return

        # ----------------------------------------------------------------
        # Step 2: load agent config from DB
        # ----------------------------------------------------------------
        async with AsyncSessionLocal() as db:
            row = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = row.scalar_one_or_none()

        if agent is None:
            await websocket.send_json({"type": "stream_error", "error": f"Agent {agent_id!r} not found."})
            return

        cfg: dict = agent.config_json or {}
        instruction: str = cfg.get("instruction", "You are a helpful assistant.")

        # ----------------------------------------------------------------
        # Step 3: conversation loop (in-memory history for multi-turn)
        # ----------------------------------------------------------------
        from agent_runtime.claw_runner import run_claw_turn

        history: list[tuple[str, str]] = []

        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=WS_INPUT_TIMEOUT)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "stream_error", "error": f"No input in {WS_INPUT_TIMEOUT}s; closing."})
                return

            user_text: str = msg.get("input", "")
            if not user_text:
                continue

            # Cooperative cancellation: check before starting
            async with AsyncSessionLocal() as check_db:
                srow = await check_db.execute(select(Session).where(Session.id == session_id))
                sess_row = srow.scalar_one_or_none()
                if sess_row and sess_row.status == "terminated":
                    await websocket.send_json({"type": "stream_error", "error": "Session terminated."})
                    return

            response_text = ""
            async for event in run_claw_turn(instruction, user_text, history):
                raw = event.get("raw", {})
                # Collect response text for history tracking
                if event.get("type") == "adk_event" and raw.get("turn_complete"):
                    response_text = raw.pop("_claw_response", "")
                await websocket.send_json(event)

                # Cooperative cancellation after each event
                async with AsyncSessionLocal() as check_db:
                    srow = await check_db.execute(select(Session).where(Session.id == session_id))
                    sess_row = srow.scalar_one_or_none()
                    if sess_row and sess_row.status == "terminated":
                        await websocket.send_json({"type": "stream_error", "error": "Session terminated."})
                        return

            # Update conversation history for next turn
            if response_text:
                history.append((user_text, response_text))

    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_json({"type": "stream_error", "error": str(exc)})
        except Exception:
            pass
