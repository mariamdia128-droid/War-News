"""add raw message dedup promotion note

Revision ID: 20260910_0058
Revises: 20260909_0057
Create Date: 2026-09-10

Generated for manual deployment; do not run automatically.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260910_0058"
down_revision: Union[str, Sequence[str], None] = "20260909_0057"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "raw_messages",
        sa.Column("dedup_promotion_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("raw_messages", "dedup_promotion_note")
