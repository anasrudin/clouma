# apps/api/schemas/agent.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AgentCreate(BaseModel):
    """Payload for POST /agents — accept a validated AgentConfig dict."""

    config: dict[str, Any]  # AgentConfig JSON (validated by validator before reaching here)


class AgentOut(BaseModel):
    id: str
    name: str
    description: str | None
    config_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
