"""merge anonymous car casualty and pipeline failure heads

Revision ID: 20260928_0068
Revises: 20260923_0063, 20260924_0067
"""

from typing import Sequence, Union

revision: str = "20260928_0068"
down_revision: Union[str, Sequence[str], None] = (
    "20260923_0063",
    "20260924_0067",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
