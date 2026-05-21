"""Runtime credential lookup for tools that need per-agent secrets."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_agent_secret(
    db: AsyncSession,
    agent_id: str,
    service: str,
    key_name: str,
) -> str | None:
    """Return the stored credential value, or None if not configured."""
    from api.models.agent_secret import AgentSecret

    result = await db.execute(
        select(AgentSecret).where(
            AgentSecret.agent_id == agent_id,
            AgentSecret.service == service,
            AgentSecret.key_name == key_name,
        )
    )
    secret = result.scalar_one_or_none()
    return secret.value if secret else None
