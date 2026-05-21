"""add_agent_secrets

Revision ID: e1f2a3b4c5d6
Revises: a3f9b2c1d4e5
Create Date: 2026-05-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'a3f9b2c1d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_secrets",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("service", sa.String(64), nullable=False),
        sa.Column("key_name", sa.String(128), nullable=False),
        sa.Column("value", sa.String(2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "service", "key_name"),
    )
    op.create_index("ix_agent_secrets_agent_id", "agent_secrets", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_secrets_agent_id", table_name="agent_secrets")
    op.drop_table("agent_secrets")
