# apps/api/routers/tools.py
from fastapi import APIRouter
from pydantic import BaseModel
from agent_runtime.tools import TOOL_REGISTRY

router = APIRouter()


class ToolDescriptor(BaseModel):
    name: str
    description: str
    input_schema: dict


@router.get("/tools", response_model=list[ToolDescriptor])
def list_tools() -> list[ToolDescriptor]:
    """Return the catalog of registered tools for UI display."""
    return [
        ToolDescriptor(
            name=entry.name,
            description=entry.description,
            input_schema=entry.input_schema,
        )
        for entry in TOOL_REGISTRY.values()
    ]
