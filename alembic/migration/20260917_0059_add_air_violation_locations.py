"""add air violation locations

Revision ID: 20260917_0059
Revises: 70c5f2978984
Create Date: 2026-09-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260917_0059"
down_revision: Union[str, Sequence[str], None] = "70c5f2978984"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "air_violations",
        sa.Column("village_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_air_violations_village_id_villages",
        "air_violations",
        "villages",
        ["village_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_air_violations_village_id",
        "air_violations",
        ["village_id"],
        unique=False,
    )
    op.create_table(
        "air_violation_locations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("air_violation_id", sa.BigInteger(), nullable=False),
        sa.Column("village_id", sa.Integer(), nullable=False),
        sa.Column("raw_location_text", sa.Text(), nullable=True),
        sa.Column("evidence_span", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["air_violation_id"],
            ["air_violations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["village_id"], ["villages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_air_violation_locations_air_violation_id",
        "air_violation_locations",
        ["air_violation_id"],
        unique=False,
    )
    op.create_index(
        "ix_air_violation_locations_village_id",
        "air_violation_locations",
        ["village_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_air_violation_locations_village_id", table_name="air_violation_locations")
    op.drop_index("ix_air_violation_locations_air_violation_id", table_name="air_violation_locations")
    op.drop_table("air_violation_locations")
    op.drop_index("ix_air_violations_village_id", table_name="air_violations")
    op.drop_constraint(
        "fk_air_violations_village_id_villages",
        "air_violations",
        type_="foreignkey",
    )
    op.drop_column("air_violations", "village_id")
