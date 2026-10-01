"""add Bazourieh village location aliases

The Air Violations audit found "من تحليق مروحية ... فوق بلدة البازورية"
stored with no village. ACS holds the village as بازورية / Bazouriye
(acs_code 62246, Sour); the news form carries the definite article, and the
Red Alert direct-text matcher normalizes without stripping ال, so it cannot
reach the reference name. The Latin forms are the spellings that appear in
press copy and are not among the three ACS names.

Revision ID: 20261001_0074
Revises: 20261001_0073
Create Date: 2026-10-01
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20261001_0074"
down_revision: Union[str, Sequence[str], None] = "20261001_0073"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO village_location_aliases
            (alias_text, alias_normalized, village_id, note, requires_geo_context, is_active)
        SELECT alias_text, alias_normalized, v.id, note, false, true
        FROM (
            VALUES
                (
                    'البازورية',
                    'البازوريه',
                    62246,
                    'Definite-article news form -> Bazouriye (Sour). ACS Arabic is بازورية.'
                ),
                (
                    'Bazourieh',
                    'bazourieh',
                    62246,
                    'Press Latin spelling -> Bazouriye (Sour). Not among the ACS names.'
                ),
                (
                    'Bazouriyeh',
                    'bazouriyeh',
                    62246,
                    'Press Latin spelling -> Bazouriye (Sour). Not among the ACS names.'
                )
        ) AS aliases(alias_text, alias_normalized, acs_code, note)
        JOIN villages v ON v.acs_code = aliases.acs_code
        ON CONFLICT (alias_normalized) DO UPDATE
        SET village_id = EXCLUDED.village_id,
            note = EXCLUDED.note,
            requires_geo_context = false,
            is_active = true
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM village_location_aliases
        WHERE alias_normalized IN ('البازوريه', 'bazourieh', 'bazouriyeh')
        AND village_id IN (
            SELECT id FROM villages WHERE acs_code = 62246
        )
        """
    )
