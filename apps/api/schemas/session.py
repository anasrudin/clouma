# apps/api/schemas/session.py
from pydantic import BaseModel
from datetime import datetime

class SessionCreate(BaseModel):
    agent_id: str

class SessionOut(BaseModel):
    id: str
    agent_id: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
