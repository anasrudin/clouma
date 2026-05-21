import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.agent import Agent
from ..models.agent_secret import AgentSecret
from ..schemas.secret import SecretCreate, SecretOut
from agent_runtime.crypto import encrypt_value

router = APIRouter()


async def _get_agent_or_404(agent_id: str, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/agents/{agent_id}/secrets", response_model=list[SecretOut])
async def list_secrets(agent_id: str, db: AsyncSession = Depends(get_db)):
    await _get_agent_or_404(agent_id, db)
    result = await db.execute(select(AgentSecret).where(AgentSecret.agent_id == agent_id))
    return result.scalars().all()


@router.post("/agents/{agent_id}/secrets", response_model=SecretOut, status_code=201)
async def upsert_secret(agent_id: str, payload: SecretCreate, db: AsyncSession = Depends(get_db)):
    await _get_agent_or_404(agent_id, db)
    result = await db.execute(
        select(AgentSecret).where(
            AgentSecret.agent_id == agent_id,
            AgentSecret.service == payload.service,
            AgentSecret.key_name == payload.key_name,
        )
    )
    from api.config import settings
    stored_value = encrypt_value(payload.value, settings.secret_encryption_key)

    secret = result.scalar_one_or_none()
    if secret:
        secret.value = stored_value
    else:
        secret = AgentSecret(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            service=payload.service,
            key_name=payload.key_name,
            value=stored_value,
        )
        db.add(secret)
    await db.commit()
    await db.refresh(secret)
    return secret


@router.delete("/agents/{agent_id}/secrets/{service}/{key_name}", status_code=204)
async def delete_secret(agent_id: str, service: str, key_name: str, db: AsyncSession = Depends(get_db)):
    await _get_agent_or_404(agent_id, db)
    result = await db.execute(
        select(AgentSecret).where(
            AgentSecret.agent_id == agent_id,
            AgentSecret.service == service,
            AgentSecret.key_name == key_name,
        )
    )
    secret = result.scalar_one_or_none()
    if secret:
        await db.delete(secret)
        await db.commit()
