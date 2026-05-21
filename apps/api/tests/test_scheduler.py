"""Tests for the cron scheduler module."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# schedule_agent
# ---------------------------------------------------------------------------

def test_schedule_agent_valid_cron_returns_true():
    with patch("agent_runtime.scheduler._scheduler") as mock_sched:
        mock_sched.add_job = MagicMock()
        from agent_runtime.scheduler import schedule_agent
        result = schedule_agent("agent-1", "0 8 * * *", "my-agent")
    assert result is True
    mock_sched.add_job.assert_called_once()


def test_schedule_agent_invalid_cron_returns_false():
    with patch("agent_runtime.scheduler._scheduler") as mock_sched:
        mock_sched.add_job = MagicMock()
        from agent_runtime.scheduler import schedule_agent
        result = schedule_agent("agent-1", "not-a-cron", "my-agent")
    assert result is False
    mock_sched.add_job.assert_not_called()


def test_schedule_agent_uses_replace_existing():
    with patch("agent_runtime.scheduler._scheduler") as mock_sched:
        mock_sched.add_job = MagicMock()
        from agent_runtime.scheduler import schedule_agent
        schedule_agent("agent-2", "0 8 * * *", "my-agent")
    _, kwargs = mock_sched.add_job.call_args
    assert kwargs.get("replace_existing") is True


def test_schedule_agent_job_id_format():
    with patch("agent_runtime.scheduler._scheduler") as mock_sched:
        mock_sched.add_job = MagicMock()
        from agent_runtime.scheduler import schedule_agent
        schedule_agent("abc-123", "0 8 * * *", "my-agent")
    _, kwargs = mock_sched.add_job.call_args
    assert kwargs.get("id") == "agent_abc-123"


def test_schedule_agent_passes_prompt():
    with patch("agent_runtime.scheduler._scheduler") as mock_sched:
        mock_sched.add_job = MagicMock()
        from agent_runtime.scheduler import schedule_agent
        schedule_agent("agent-3", "0 8 * * *", "my-agent", prompt="Do the thing")
    _, kwargs = mock_sched.add_job.call_args
    assert "Do the thing" in kwargs.get("args", [])


# ---------------------------------------------------------------------------
# unschedule_agent
# ---------------------------------------------------------------------------

def test_unschedule_agent_removes_existing_job():
    mock_job = MagicMock()
    with patch("agent_runtime.scheduler._scheduler") as mock_sched:
        mock_sched.get_job.return_value = mock_job
        mock_sched.remove_job = MagicMock()
        from agent_runtime.scheduler import unschedule_agent
        unschedule_agent("agent-4")
    mock_sched.remove_job.assert_called_once_with("agent_agent-4")


def test_unschedule_nonexistent_agent_is_noop():
    with patch("agent_runtime.scheduler._scheduler") as mock_sched:
        mock_sched.get_job.return_value = None
        mock_sched.remove_job = MagicMock()
        from agent_runtime.scheduler import unschedule_agent
        unschedule_agent("ghost-agent")  # must not raise
    mock_sched.remove_job.assert_not_called()


# ---------------------------------------------------------------------------
# get_scheduled_jobs
# ---------------------------------------------------------------------------

def test_get_scheduled_jobs_returns_list():
    mock_job = MagicMock()
    mock_job.id = "agent_agent-5"
    mock_job.args = ["agent-5", "agent-five", "Run task"]
    mock_job.next_run_time = None

    with patch("agent_runtime.scheduler._scheduler") as mock_sched:
        mock_sched.get_jobs.return_value = [mock_job]
        from agent_runtime.scheduler import get_scheduled_jobs
        jobs = get_scheduled_jobs()

    assert len(jobs) == 1
    assert jobs[0]["agent_id"] == "agent-5"
    assert jobs[0]["agent_name"] == "agent-five"
    assert jobs[0]["next_run"] is None


def test_get_scheduled_jobs_ignores_non_agent_jobs():
    mock_other = MagicMock()
    mock_other.id = "heartbeat"  # not an agent_ job

    with patch("agent_runtime.scheduler._scheduler") as mock_sched:
        mock_sched.get_jobs.return_value = [mock_other]
        from agent_runtime.scheduler import get_scheduled_jobs
        jobs = get_scheduled_jobs()

    assert jobs == []


# ---------------------------------------------------------------------------
# start_scheduler idempotent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_scheduler_idempotent():
    """Calling start_scheduler twice must not call _scheduler.start() twice."""
    with patch("agent_runtime.scheduler._scheduler") as mock_sched:
        mock_sched.running = False

        with patch("api.database.AsyncSessionLocal") as mock_sl:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_ctx.execute = AsyncMock(return_value=mock_result)
            mock_sl.return_value = mock_ctx

            from agent_runtime.scheduler import start_scheduler
            await start_scheduler()

            # Now pretend it's running
            mock_sched.running = True
            await start_scheduler()  # second call must return early

        # start() called exactly once
        mock_sched.start.assert_called_once()
