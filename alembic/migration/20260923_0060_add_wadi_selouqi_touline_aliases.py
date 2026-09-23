"""add Wadi el-Selouqi aliases for Touline

Revision ID: 20260923_0060
Revises: baee92272194
Create Date: 2026-09-23
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260923_0060"
down_revision: Union[str, Sequence[str], None] = "baee92272194"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ALIASES: tuple[tuple[str, str, str], ...] = (
    (
        "وادي السلوقي",
        "وادي السلوقي",
        "Wadi el-Selouqi recurring southern valley reference -> Touline (Marjaayoun), not Slouqi/Slouky Baalbek.",
    ),
    (
        "السلوقي",
        "السلوقي",
        "Extractor may strip وادي; same Wadi el-Selouqi context -> Touline.",
    ),
    (
        "وادي سلوقي",
        "وادي سلوقي",
        "Spelling variant for Wadi el-Selouqi -> Touline.",
    ),
    (
        "wadi selouqi",
        "wadi selouqi",
        "Latin variant for Wadi el-Selouqi -> Touline.",
    ),
    (
        "wadi salouqi",
        "wadi salouqi",
        "Latin variant for Wadi el-Selouqi -> Touline.",
    ),
)


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO village_location_aliases
            (alias_text, alias_normalized, village_id, note, requires_geo_context, is_active)
        SELECT alias_text, alias_normalized, v.id, note, false, true
        FROM (
            VALUES
                ('وادي السلوقي', 'وادي السلوقي', 'Wadi el-Selouqi recurring southern valley reference -> Touline (Marjaayoun), not Slouqi/Slouky Baalbek.'),
                ('السلوقي', 'السلوقي', 'Extractor may strip وادي; same Wadi el-Selouqi context -> Touline.'),
                ('وادي سلوقي', 'وادي سلوقي', 'Spelling variant for Wadi el-Selouqi -> Touline.'),
                ('wadi selouqi', 'wadi selouqi', 'Latin variant for Wadi el-Selouqi -> Touline.'),
                ('wadi salouqi', 'wadi salouqi', 'Latin variant for Wadi el-Selouqi -> Touline.')
        ) AS aliases(alias_text, alias_normalized, note)
        JOIN villages v ON v.acs_code = 73282
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
        WHERE alias_normalized IN (
            'وادي السلوقي',
            'السلوقي',
            'وادي سلوقي',
            'wadi selouqi',
            'wadi salouqi'
        )
        AND village_id IN (SELECT id FROM villages WHERE acs_code = 73282)
        """
    )
