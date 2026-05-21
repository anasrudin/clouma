# apps/api/routers/scheduled.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ScheduledJobOut(BaseModel):
    agent_id: str
    agent_name: str
    prompt: str
    next_run: str | None


@router.get("/scheduled-agents", response_model=list[ScheduledJobOut])
def list_scheduled_agents() -> list[ScheduledJobOut]:
    """Return all agents currently registered in the cron scheduler."""
    from agent_runtime.scheduler import get_scheduled_jobs
    return [ScheduledJobOut(**job) for job in get_scheduled_jobs()]
