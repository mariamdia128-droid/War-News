"""add incident verification flags

Revision ID: 20260928_0070
Revises: 20260928_0069
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260928_0070"
down_revision: Union[str, None] = "20260928_0069"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incident_verification_flags",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flag_type", sa.String(length=48), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="open", nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("auto_clear_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('open', 'resolved', 'dismissed', 'auto_cleared')",
            name="ck_incident_verification_flags_status",
        ),
        sa.CheckConstraint(
            "severity IN ('review', 'info')",
            name="ck_incident_verification_flags_severity",
        ),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_message_id"], ["raw_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_incident_verification_flags_open_key",
        "incident_verification_flags",
        ["incident_id", "flag_type", "reason_code"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )
    op.create_index(
        "ix_incident_verification_flags_type_status",
        "incident_verification_flags",
        ["flag_type", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_incident_verification_flags_type_status", table_name="incident_verification_flags")
    op.drop_index("uq_incident_verification_flags_open_key", table_name="incident_verification_flags")
    op.drop_table("incident_verification_flags")
