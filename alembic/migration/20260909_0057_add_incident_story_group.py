"""add incident story_group_id for sub-event linking

Revision ID: 20260909_0057
Revises: 20260909_0056
Create Date: 2026-09-09

Generated for manual deployment; do not run automatically.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260909_0057"
down_revision: Union[str, Sequence[str], None] = "20260909_0056"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("story_group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_incidents_story_group_id",
        "incidents",
        ["story_group_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_incidents_story_group_id", table_name="incidents")
    op.drop_column("incidents", "story_group_id")
