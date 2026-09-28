"""persist casualty type statuses and delayed flag visibility

Revision ID: 20260928_0071
Revises: 20260928_0070
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260928_0071"
down_revision: Union[str, None] = "20260928_0070"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATUS_VALUES = "('none_mentioned', 'explicit_none', 'exact', 'count_missing', 'aggregate_only')"


def upgrade() -> None:
    op.add_column("incidents", sa.Column("casualty_deaths_status", sa.String(24), nullable=True))
    op.add_column("incidents", sa.Column("casualty_injuries_status", sa.String(24), nullable=True))
    op.add_column(
        "incidents",
        sa.Column("casualty_status_remaining_total", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    for name, column in (
        ("ck_incidents_casualty_deaths_status", "casualty_deaths_status"),
        ("ck_incidents_casualty_injuries_status", "casualty_injuries_status"),
    ):
        op.create_check_constraint(name, "incidents", f"{column} IS NULL OR {column} IN {_STATUS_VALUES}")

    op.add_column(
        "incident_verification_flags",
        sa.Column("visible_after", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_index("ix_incident_verification_flags_type_status", table_name="incident_verification_flags")
    op.create_index(
        "ix_incident_verification_flags_type_status_visible_after",
        "incident_verification_flags",
        ["flag_type", "status", "visible_after"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_incident_verification_flags_type_status_visible_after",
        table_name="incident_verification_flags",
    )
    op.create_index(
        "ix_incident_verification_flags_type_status",
        "incident_verification_flags",
        ["flag_type", "status"],
    )
    op.drop_column("incident_verification_flags", "visible_after")
    op.drop_constraint("ck_incidents_casualty_injuries_status", "incidents", type_="check")
    op.drop_constraint("ck_incidents_casualty_deaths_status", "incidents", type_="check")
    op.drop_column("incidents", "casualty_status_remaining_total")
    op.drop_column("incidents", "casualty_injuries_status")
    op.drop_column("incidents", "casualty_deaths_status")
