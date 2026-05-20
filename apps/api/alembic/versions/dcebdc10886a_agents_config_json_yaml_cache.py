"""agents config_json + yaml_cache

Revision ID: dcebdc10886a
Revises:
Create Date: 2026-05-21 00:00:00.000000

NOTE: This migration requires a running Postgres instance.
      It has NOT been applied automatically; run manually with:
          cd apps/api && alembic upgrade head
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dcebdc10886a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("yaml_cache", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_agents_name"),
    )
    op.create_index("ix_agents_name", "agents", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_agents_name", table_name="agents")
    op.drop_table("agents")
