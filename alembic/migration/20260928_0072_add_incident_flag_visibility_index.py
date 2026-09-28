"""add incident-first verification flag visibility index

Revision ID: 20260928_0072
Revises: 20260928_0071
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260928_0072"
down_revision: Union[str, None] = "20260928_0071"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_incident_verification_flags_incident_status_visible_after",
        "incident_verification_flags",
        ["incident_id", "status", "visible_after"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_incident_verification_flags_incident_status_visible_after",
        table_name="incident_verification_flags",
    )
