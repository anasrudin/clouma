# apps/api/schemas/agent.py
from pydantic import BaseModel
from datetime import datetime

class AgentCreate(BaseModel):
    name: str
    yaml_config: str

class AgentOut(BaseModel):
    id: str
    name: str
    yaml_config: str
    json_config: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class CompileRequest(BaseModel):
    prompt: str
