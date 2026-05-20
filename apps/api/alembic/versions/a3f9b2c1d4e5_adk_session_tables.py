"""adk_sessions + adk_session_events tables

Revision ID: a3f9b2c1d4e5
Revises: dcebdc10886a
Create Date: 2026-05-21 00:00:00.000000

NOTE: This migration requires a running Postgres instance.
      It has NOT been applied automatically; run manually with:
          cd apps/api && alembic upgrade head

Design notes:
- adk_sessions stores session metadata with a float unix timestamp for
  last_update_time (matching ADK's Session.last_update_time field).
- adk_session_events stores events as opaque JSON blobs — per ADK 2.0 docs,
  this avoids schema rewrites when new fields (node_info, output) are added.
- No foreign-key constraint between events and sessions so that the tables
  remain usable with SQLite during tests.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f9b2c1d4e5"
down_revision: Union[str, None] = "dcebdc10886a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "adk_sessions",
        sa.Column("id", sa.String(64), primary_key=True, nullable=False),
        sa.Column("app_name", sa.String(128), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_update_time", sa.Float(), nullable=False),
    )
    op.create_index("ix_adk_sessions_app_name", "adk_sessions", ["app_name"])
    op.create_index("ix_adk_sessions_user_id", "adk_sessions", ["user_id"])

    op.create_table(
        "adk_session_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("event_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=False),
    )
    op.create_index(
        "ix_adk_session_events_session_id", "adk_session_events", ["session_id"]
    )
    op.create_index(
        "ix_adk_session_events_timestamp", "adk_session_events", ["timestamp"]
    )
    op.create_index(
        "ix_adk_session_events_session_ts",
        "adk_session_events",
        ["session_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_adk_session_events_session_ts", table_name="adk_session_events")
    op.drop_index(
        "ix_adk_session_events_timestamp", table_name="adk_session_events"
    )
    op.drop_index(
        "ix_adk_session_events_session_id", table_name="adk_session_events"
    )
    op.drop_table("adk_session_events")

    op.drop_index("ix_adk_sessions_user_id", table_name="adk_sessions")
    op.drop_index("ix_adk_sessions_app_name", table_name="adk_sessions")
    op.drop_table("adk_sessions")
