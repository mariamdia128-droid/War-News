"""add air violation backfill fields

Revision ID: baee92272194
Revises: 20260917_0059
Create Date: 2026-09-17 08:44:13.467829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "baee92272194"
down_revision: Union[str, Sequence[str], None] = "20260917_0059"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("air_violations", sa.Column("window_id", sa.String(), nullable=True))
    op.add_column("air_violations", sa.Column("review_status", sa.String(), nullable=True))
    op.add_column("air_violations", sa.Column("review_reason", sa.Text(), nullable=True))
    op.create_index(
        "ix_air_violations_window_id",
        "air_violations",
        ["window_id"],
        unique=False,
    )
    op.create_index(
        "ix_air_violations_review_status",
        "air_violations",
        ["review_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_air_violations_review_status", table_name="air_violations")
    op.drop_index("ix_air_violations_window_id", table_name="air_violations")
    op.drop_column("air_violations", "review_reason")
    op.drop_column("air_violations", "review_status")
    op.drop_column("air_violations", "window_id")