"""add nullable derived casualty status to incidents

Revision ID: 20260928_0069
Revises: 20260928_0068
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260928_0069"
down_revision: Union[str, None] = "20260928_0068"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("casualty_status", sa.String(length=24), nullable=True))
    op.add_column("incidents", sa.Column("casualty_is_preliminary", sa.Boolean(), nullable=True))
    op.add_column("incidents", sa.Column("casualty_status_evidence", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_incidents_casualty_status",
        "incidents",
        "casualty_status IS NULL OR casualty_status IN "
        "('none_mentioned', 'explicit_none', 'exact', 'count_missing', 'aggregate_only')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_incidents_casualty_status", "incidents", type_="check")
    op.drop_column("incidents", "casualty_status_evidence")
    op.drop_column("incidents", "casualty_is_preliminary")
    op.drop_column("incidents", "casualty_status")
