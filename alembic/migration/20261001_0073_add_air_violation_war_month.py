"""add air violation war month

Revision ID: 20261001_0073
Revises: 20260928_0072
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261001_0073"
down_revision: Union[str, None] = "20260928_0072"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "air_violations",
        sa.Column("war_month", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("air_violations", "war_month")
