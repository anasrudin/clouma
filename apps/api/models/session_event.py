# apps/api/models/session_event.py
"""ORM models for ADK session persistence.

Design principle (ADK 2.0 doc):
  Events are stored as opaque JSON blobs so that new ADK fields (node_info,
  output, etc.) do not require schema rewrites.  Only session metadata uses
  typed columns.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database import Base


class SessionRow(Base):
    """Persists ADK Session metadata.

    Events are stored separately in EventRow as opaque JSON blobs.
    """

    __tablename__ = "adk_sessions"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True
    )  # ADK session id (uuid string)
    app_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    state_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # ADK uses a unix float timestamp for last_update_time
    last_update_time: Mapped[float] = mapped_column(Float, nullable=False)


class EventRow(Base):
    """Stores ADK Events as opaque JSON blobs.

    Using JSON blobs (not rigid columns) means new ADK 2.0 fields like
    node_info and output are stored transparently without schema changes.
    """

    __tablename__ = "adk_session_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    __table_args__ = (
        Index("ix_adk_session_events_session_ts", "session_id", "timestamp"),
    )
