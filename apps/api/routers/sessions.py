# apps/api/routers/sessions.py
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models.session import Session
from ..models.agent import Agent
from ..schemas.session import SessionCreate, SessionOut

router = APIRouter()

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

@router.websocket("/sessions/{session_id}/stream")
async def stream_session(session_id: str, websocket: WebSocket):
    await websocket.accept()
    try:
        # Simulate agent execution events for MVP
        events = [
            {"type": "status", "status": "running"},
            {"type": "token", "content": "Starting agent execution..."},
            {"type": "tool_call", "tool": "web_search", "input": "trending AI startups 2026"},
            {"type": "token", "content": "Searching the web..."},
            {"type": "tool_result", "tool": "web_search", "output": "Found 10 results about AI startups."},
            {"type": "token", "content": "Compiling summary..."},
            {"type": "checkpoint", "step": 1, "state": "search_complete"},
            {"type": "tool_call", "tool": "telegram_send", "input": "Summary: Top AI startups this week..."},
            {"type": "tool_result", "tool": "telegram_send", "output": "Message sent successfully."},
            {"type": "status", "status": "completed"},
        ]
        for event in events:
            await websocket.send_text(json.dumps(event))
            await asyncio.sleep(0.8)
    except WebSocketDisconnect:
        pass
