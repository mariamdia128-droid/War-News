"""add conditional village location aliases

Revision ID: 70c5f2978984
Revises: 20260910_0058
Create Date: 2026-09-16 09:37:09.031448

Generated for manual deployment; do not run automatically.
Reference-data rows are intentionally kept in a separate manual-review SQL file.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "70c5f2978984"
down_revision: Union[str, Sequence[str], None] = "20260910_0058"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "village_location_aliases",
        sa.Column(
            "requires_geo_context",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("village_location_aliases", "requires_geo_context")
