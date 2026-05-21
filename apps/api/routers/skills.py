# apps/api/routers/skills.py
from fastapi import APIRouter
from pydantic import BaseModel

from agent_runtime.skills import SKILL_REGISTRY

router = APIRouter()


class SkillDescriptor(BaseModel):
    name: str
    description: str
    tool_names: list[str]


@router.get("/skills", response_model=list[SkillDescriptor])
def list_skills() -> list[SkillDescriptor]:
    """Return the catalog of registered skills for UI display."""
    return [
        SkillDescriptor(
            name=entry.name,
            description=entry.description,
            tool_names=list(entry.tool_names),
        )
        for entry in SKILL_REGISTRY.values()
    ]
