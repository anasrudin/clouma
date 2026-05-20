# apps/api/routers/agents.py
import json
import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models.agent import Agent
from ..schemas.agent import AgentCreate, AgentOut, CompileRequest
from ..services.compiler import compile_prompt_to_yaml

router = APIRouter()

@router.post("/agents/compile")
async def compile_agent(req: CompileRequest):
    async def generate():
        async for token in compile_prompt_to_yaml(req.prompt):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.post("/agents", response_model=AgentOut)
async def create_agent(req: AgentCreate, db: AsyncSession = Depends(get_db)):
    try:
        parsed = yaml.safe_load(req.yaml_config)
        json_config = json.dumps(parsed)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid YAML")

    agent = Agent(name=req.name, yaml_config=req.yaml_config, json_config=json_config)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent

@router.get("/agents", response_model=list[AgentOut])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return result.scalars().all()

@router.get("/agents/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()
    return {"ok": True}
