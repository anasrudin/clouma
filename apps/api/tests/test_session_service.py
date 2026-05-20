# apps/api/tests/test_session_service.py
"""Tests for PostgresSessionService (Phase 4A).

Uses SQLite in-memory via aiosqlite — same pattern as Phase 3 tests.
The JSON blob approach means SQLite JSON columns work identically to Postgres
jsonb for our purposes (event round-trip through model_dump / model_validate).
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from google.adk.events.event import Event
from google.genai import types

from api.database import Base
from api.models.session_event import SessionRow, EventRow  # registers ORM models
from api.agent_runtime.session_service import PostgresSessionService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def sessionmaker_fixture():
    """In-memory SQLite async sessionmaker with tables created."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    yield sm
    await engine.dispose()


@pytest_asyncio.fixture()
async def service(sessionmaker_fixture):
    """PostgresSessionService backed by in-memory SQLite."""
    return PostgresSessionService(sessionmaker_fixture)


def _make_event(author: str = "user", text: str = "hello") -> Event:
    """Create a minimal non-partial ADK Event."""
    return Event(
        author=author,
        content=types.Content(parts=[types.Part(text=text)]),
    )


# ---------------------------------------------------------------------------
# Test 1: create_session persists row to DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_persists_to_db(service, sessionmaker_fixture):
    session = await service.create_session(app_name="testapp", user_id="u1")

    async with sessionmaker_fixture() as db:
        result = await db.execute(
            select(SessionRow).where(SessionRow.id == session.id)
        )
        row = result.scalar_one_or_none()

    assert row is not None
    assert row.app_name == "testapp"
    assert row.user_id == "u1"
    assert row.last_update_time > 0


# ---------------------------------------------------------------------------
# Test 2: get_session returns persisted session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_session_returns_persisted_session(service):
    created = await service.create_session(app_name="myapp", user_id="user42")

    fetched = await service.get_session(
        app_name="myapp",
        user_id="user42",
        session_id=created.id,
    )

    assert fetched is not None
    assert fetched.app_name == "myapp"
    assert fetched.user_id == "user42"
    assert fetched.id == created.id
    assert fetched.events == []


# ---------------------------------------------------------------------------
# Test 3: append_event stores event as JSON blob
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_append_event_stores_as_blob(service, sessionmaker_fixture):
    session = await service.create_session(app_name="blobapp", user_id="blobuser")
    event = _make_event(author="user", text="hi")

    await service.append_event(session, event)

    # Query the raw adk_session_events table
    async with sessionmaker_fixture() as db:
        result = await db.execute(
            select(EventRow).where(EventRow.session_id == session.id)
        )
        rows = list(result.scalars().all())

    assert len(rows) == 1
    blob = rows[0].event_json
    assert isinstance(blob, dict)
    assert blob.get("author") == "user"


# ---------------------------------------------------------------------------
# Test 4: get_session replays events in order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_session_replays_events(service):
    session = await service.create_session(app_name="replayapp", user_id="ru1")

    event1 = _make_event(author="user", text="first")
    event2 = _make_event(author="agent", text="second")

    await service.append_event(session, event1)
    await service.append_event(session, event2)

    fetched = await service.get_session(
        app_name="replayapp",
        user_id="ru1",
        session_id=session.id,
    )

    assert fetched is not None
    assert len(fetched.events) == 2
    # Events should be in chronological order
    assert fetched.events[0].author == "user"
    assert fetched.events[1].author == "agent"


# ---------------------------------------------------------------------------
# Test 5: list_sessions filters by user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sessions_filters_by_user(service):
    await service.create_session(app_name="listapp", user_id="user1")
    await service.create_session(app_name="listapp", user_id="user1")
    await service.create_session(app_name="listapp", user_id="user2")

    response = await service.list_sessions(app_name="listapp", user_id="user1")

    assert len(response.sessions) == 2
    for s in response.sessions:
        assert s.user_id == "user1"


# ---------------------------------------------------------------------------
# Test 6: delete_session removes session + event rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_session_removes_rows(service, sessionmaker_fixture):
    session = await service.create_session(app_name="delapp", user_id="du1")
    event = _make_event(author="user", text="bye")
    await service.append_event(session, event)

    await service.delete_session(
        app_name="delapp",
        user_id="du1",
        session_id=session.id,
    )

    async with sessionmaker_fixture() as db:
        sess_result = await db.execute(
            select(SessionRow).where(SessionRow.id == session.id)
        )
        evt_result = await db.execute(
            select(EventRow).where(EventRow.session_id == session.id)
        )
        sess_row = sess_result.scalar_one_or_none()
        evt_rows = list(evt_result.scalars().all())

    assert sess_row is None, "session row should be deleted"
    assert evt_rows == [], "event rows should be deleted"


# ---------------------------------------------------------------------------
# Test 7: append_event raises ValueError when session has been deleted (I2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_append_event_raises_when_session_deleted(service):
    """append_event must raise ValueError if the SessionRow is gone.

    Regression guard: previously the missing-row branch was a silent no-op,
    meaning the caller got back an event that was never actually persisted.
    """
    session = await service.create_session(app_name="raiseapp", user_id="ru1")

    # Delete the session out-of-band (simulates concurrent deletion)
    await service.delete_session(
        app_name="raiseapp",
        user_id="ru1",
        session_id=session.id,
    )

    event = _make_event(author="user", text="ghost write")

    with pytest.raises(ValueError, match=session.id):
        await service.append_event(session, event)
