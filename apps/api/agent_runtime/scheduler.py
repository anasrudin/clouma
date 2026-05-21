"""Agent cron scheduler.

Loads all agents with a `schedule` field from the DB on startup and registers
them as APScheduler cron jobs. When an agent is created, updated, or deleted,
the caller should invoke schedule_agent() / unschedule_agent() accordingly.

Cron format: standard 5-field crontab  "MIN HOUR DOM MON DOW"
Example:     "0 8 * * *"  → every day at 08:00 UTC

The scheduler job calls build_runner() and executes one turn using the
agent's optional `schedule_prompt` (or a default). Events are persisted by
PostgresSessionService so they appear in the session history.
"""

from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")

DEFAULT_SCHEDULE_PROMPT = "Run your scheduled task."


# ---------------------------------------------------------------------------
# Job function — called by APScheduler
# ---------------------------------------------------------------------------

async def _run_agent_job(agent_id: str, app_name: str, prompt: str) -> None:
    """Execute one scheduled turn for an agent."""
    from api.database import AsyncSessionLocal
    from agent_runtime.runner_factory import build_runner
    from google.genai.types import Content, Part

    logger.info("Running scheduled agent %s (%s)", agent_id, app_name)
    try:
        runner = await build_runner(agent_id, AsyncSessionLocal, app_name=app_name)
        session = await runner.session_service.create_session(
            app_name=app_name, user_id="scheduler"
        )
        message = Content(role="user", parts=[Part(text=prompt)])
        async for _ in runner.run_async(
            user_id="scheduler", session_id=session.id, new_message=message
        ):
            pass
        logger.info("Scheduled run complete for agent %s", agent_id)
    except Exception as exc:
        logger.error("Scheduled agent %s failed: %s", agent_id, exc, exc_info=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def schedule_agent(agent_id: str, cron_expr: str, app_name: str, prompt: str = DEFAULT_SCHEDULE_PROMPT) -> bool:
    """Add or replace a cron job for an agent.

    Args:
        agent_id:   UUID of the agent.
        cron_expr:  Standard 5-field crontab string, e.g. "0 8 * * *".
        app_name:   Human-readable name used as the ADK app_name.
        prompt:     Message sent to the agent each run.

    Returns:
        True on success, False if cron_expr is invalid.
    """
    try:
        trigger = CronTrigger.from_crontab(cron_expr, timezone="UTC")
    except (ValueError, KeyError):
        logger.warning("Invalid cron expression for agent %s: %r", agent_id, cron_expr)
        return False

    _scheduler.add_job(
        _run_agent_job,
        trigger=trigger,
        args=[agent_id, app_name, prompt],
        id=f"agent_{agent_id}",
        replace_existing=True,
        misfire_grace_time=60,  # allow 60s of latency before skipping a run
    )
    logger.info("Scheduled agent %s with cron %r", agent_id, cron_expr)
    return True


def unschedule_agent(agent_id: str) -> None:
    """Remove the cron job for an agent if it exists."""
    job_id = f"agent_{agent_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
        logger.info("Unscheduled agent %s", agent_id)


def get_scheduled_jobs() -> list[dict[str, Any]]:
    """Return info about all currently scheduled agent jobs."""
    jobs = []
    for job in _scheduler.get_jobs():
        if not job.id.startswith("agent_"):
            continue
        agent_id, app_name, prompt = job.args
        jobs.append({
            "agent_id": agent_id,
            "agent_name": app_name,
            "prompt": prompt,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    return jobs


# ---------------------------------------------------------------------------
# Lifecycle — called from FastAPI lifespan
# ---------------------------------------------------------------------------

async def start_scheduler() -> None:
    """Start the scheduler and load all scheduled agents from the DB."""
    from sqlalchemy import select
    from api.database import AsyncSessionLocal
    from api.models.agent import Agent

    if _scheduler.running:
        return  # idempotent — second TestClient or hot-reload should not re-start

    _scheduler.start()
    logger.info("Scheduler started")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agent))
        agents = result.scalars().all()

    loaded = 0
    for agent in agents:
        cron_expr = agent.config_json.get("schedule")
        if cron_expr:
            prompt = agent.config_json.get("schedule_prompt", DEFAULT_SCHEDULE_PROMPT)
            if schedule_agent(agent.id, cron_expr, agent.name, prompt):
                loaded += 1

    logger.info("Loaded %d scheduled agent(s) from DB", loaded)


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
