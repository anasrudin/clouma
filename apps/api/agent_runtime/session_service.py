# apps/api/agent_runtime/session_service.py
"""Postgres-backed ADK session service.

Implements google.adk.sessions.BaseSessionService using two SQLAlchemy tables:
  - adk_sessions   — session metadata (id, app_name, user_id, state, timestamps)
  - adk_session_events — events stored as opaque JSON blobs (ADK 2.0 pattern)

JSON-blob storage means new ADK fields (node_info, output, etc.) are stored
and replayed transparently without requiring schema migrations.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from google.adk.platform import time as platform_time
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from typing_extensions import override

from api.models.session_event import EventRow, SessionRow


class PostgresSessionService(BaseSessionService):
    """SQLAlchemy-backed session service that persists events as JSON blobs.

    Parameters
    ----------
    sessionmaker:
        An ``async_sessionmaker[AsyncSession]`` factory bound to the project
        database engine.  Inject the application's ``AsyncSessionLocal`` or a
        test-scoped sessionmaker.
    """

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    # ------------------------------------------------------------------
    # create_session
    # ------------------------------------------------------------------

    @override
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Create and persist a new session."""
        sid = (session_id or str(uuid.uuid4())).strip() or str(uuid.uuid4())
        now = platform_time.get_time()
        session_state: dict[str, Any] = state or {}

        row = SessionRow(
            id=sid,
            app_name=app_name,
            user_id=user_id,
            state_json=session_state,
            last_update_time=now,
        )

        async with self._sessionmaker() as db:
            db.add(row)
            await db.commit()

        return Session(
            id=sid,
            app_name=app_name,
            user_id=user_id,
            state=dict(session_state),
            events=[],
            last_update_time=now,
        )

    # ------------------------------------------------------------------
    # get_session
    # ------------------------------------------------------------------

    @override
    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        """Load a session from the database, replaying events from JSON blobs."""
        async with self._sessionmaker() as db:
            # Load session row
            result = await db.execute(
                select(SessionRow).where(SessionRow.id == session_id)
            )
            row: Optional[SessionRow] = result.scalar_one_or_none()
            if row is None:
                return None
            if row.app_name != app_name or row.user_id != user_id:
                return None

            # Load events ordered by timestamp
            stmt = (
                select(EventRow)
                .where(EventRow.session_id == session_id)
                .order_by(EventRow.timestamp.asc())
            )

            # Apply config filters
            if config is not None:
                if config.after_timestamp is not None:
                    stmt = stmt.where(EventRow.timestamp >= config.after_timestamp)

            event_result = await db.execute(stmt)
            event_rows = list(event_result.scalars().all())

        # Rehydrate events from JSON blobs (handles all ADK 2.0 fields)
        events: list[Event] = [
            Event.model_validate(er.event_json) for er in event_rows
        ]

        # Apply num_recent_events limit (after timestamp filter)
        if config is not None and config.num_recent_events is not None:
            if config.num_recent_events == 0:
                events = []
            else:
                events = events[-config.num_recent_events :]

        return Session(
            id=row.id,
            app_name=row.app_name,
            user_id=row.user_id,
            state=dict(row.state_json or {}),
            events=events,
            last_update_time=row.last_update_time,
        )

    # ------------------------------------------------------------------
    # list_sessions
    # ------------------------------------------------------------------

    @override
    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        """List sessions for an app (optionally filtered by user).

        Per ADK contract, returned Session objects have events=[] and states set.
        """
        async with self._sessionmaker() as db:
            stmt = select(SessionRow).where(SessionRow.app_name == app_name)
            if user_id is not None:
                stmt = stmt.where(SessionRow.user_id == user_id)

            result = await db.execute(stmt)
            rows = list(result.scalars().all())

        sessions = [
            Session(
                id=r.id,
                app_name=r.app_name,
                user_id=r.user_id,
                state=dict(r.state_json or {}),
                events=[],
                last_update_time=r.last_update_time,
            )
            for r in rows
        ]
        return ListSessionsResponse(sessions=sessions)

    # ------------------------------------------------------------------
    # delete_session
    # ------------------------------------------------------------------

    @override
    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        """Delete a session and all its events."""
        async with self._sessionmaker() as db:
            # Delete events first (no FK cascade in our schema)
            await db.execute(
                delete(EventRow).where(EventRow.session_id == session_id)
            )
            await db.execute(
                delete(SessionRow).where(
                    SessionRow.id == session_id,
                    SessionRow.app_name == app_name,
                    SessionRow.user_id == user_id,
                )
            )
            await db.commit()

    # ------------------------------------------------------------------
    # append_event  (override to also persist to DB)
    # ------------------------------------------------------------------

    @override
    async def append_event(self, session: Session, event: Event) -> Event:
        """Append an event to the session, persisting it as a JSON blob.

        Calls super().append_event() first (handles partial events, state
        deltas, temp state trimming), then persists to DB.
        """
        # Let base class handle partial/temp state logic
        event = await super().append_event(session, event)

        if event.partial:
            # Base class returns early for partial events — nothing to persist
            return event

        # Serialize the full event as an opaque JSON blob
        event_blob = event.model_dump(mode="json")

        async with self._sessionmaker() as db:
            # Persist the event blob
            db.add(
                EventRow(
                    session_id=session.id,
                    event_json=event_blob,
                    timestamp=event.timestamp,
                )
            )

            # Update session's last_update_time and state in DB
            result = await db.execute(
                select(SessionRow).where(SessionRow.id == session.id)
            )
            row: Optional[SessionRow] = result.scalar_one_or_none()
            if row is not None:
                row.last_update_time = event.timestamp
                # Persist non-temp session state delta
                if event.actions.state_delta:
                    merged = dict(row.state_json or {})
                    merged.update(
                        {
                            k: v
                            for k, v in event.actions.state_delta.items()
                            if not k.startswith("temp:")
                        }
                    )
                    row.state_json = merged

            await db.commit()

        return event
