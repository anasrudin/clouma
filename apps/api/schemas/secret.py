from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SecretCreate(BaseModel):
    service: str
    key_name: str
    value: str


class SecretOut(BaseModel):
    id: str
    service: str
    key_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
