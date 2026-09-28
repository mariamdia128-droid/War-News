"""add confirmed no-ACS place aliases and incident display names

Revision ID: 20260923_0061
Revises: 20260923_0060
Create Date: 2026-09-23
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260923_0061"
down_revision: Union[str, Sequence[str], None] = "20260923_0060"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ALIASES: tuple[tuple[str, int, str], ...] = (
    ("البياضة", 62299, "Confirmed no-ACS local name -> Iskandarouna Sour."),
    ("محمية وادي الحجير", 73262, "Confirmed no-ACS local name -> Qabrikha."),
    ("محرونة", 62215, "Confirmed no-ACS local name -> Mazraat Mechref."),
    ("بيوت السياد", 62296, "Confirmed no-ACS local name -> Mansouri Sour."),
    ("السماعية", 62179, "Confirmed no-ACS local name -> Deir Qanoun El-Aain."),
    ("المعلية", 62179, "Confirmed no-ACS local name -> Deir Qanoun El-Aain."),
    ("المالكية", 62277, "Confirmed no-ACS local name -> Chaaitiye."),
    ("لبونة", 62316, "Confirmed no-ACS local name -> Aalma Ech-Chaab."),
    ("الناقورة", 62312, "Confirmed no-ACS local name -> Borj En-Naqoura."),
    ("الدبشة", 71133, "Confirmed no-ACS local name -> Kfar Roummane."),
    ("جبل الرفيع", 71133, "Confirmed no-ACS local name -> Kfar Roummane."),
    ("وادي راج", 71367, "Confirmed no-ACS local name -> Zaoutar Ech-Charqiye."),
    ("الوزاني", 74141, "Confirmed no-ACS local name -> Salaiyeb."),
    ("وادي الحير", 74118, "Confirmed no-ACS local name -> Rachaiya El-Foukhar."),
    ("وادي إسطبل", 73234, "Confirmed no-ACS local name -> Houla."),
    ("وادي الجمل", 73250, "Confirmed no-ACS local name -> Meiss Ej-Jabal."),
    ("خلة الدواوير", 72229, "Confirmed no-ACS local name -> Chaqra."),
    ("عريض الماريحيا", 73282, "Confirmed no-ACS local name -> Touline."),
    ("حوشين", 73250, "Confirmed no-ACS local name -> Meiss Ej-Jabal."),
    ("خلة الساقية", 73234, "Confirmed no-ACS local name -> Houla."),
    ("ابو مكنا", 73232, "Confirmed no-ACS local name -> Taybet Matjaayoun."),
    ("شانوح", 74160, "Confirmed no-ACS local name -> Kfar Chouba."),
    ("الرمثا", 74160, "Confirmed no-ACS local name -> Kfar Chouba."),
    ("وادي حسن", 62297, "Confirmed no-ACS local name -> Majdelzoun."),
    ("جبل الوردة", 73245, "Confirmed no-ACS local name -> Markaba."),
    ("جسر الخردلي", 73151, "Confirmed no-ACS local name -> Qlaiaa."),
)


def upgrade() -> None:
    op.add_column("incidents", sa.Column("village_display_name", sa.String(), nullable=True))
    alias_values = sa.table(
        "alias_values",
        sa.column("alias_text", sa.String()),
        sa.column("acs_code", sa.Integer()),
        sa.column("note", sa.String()),
    )
    village_location_aliases = sa.table(
        "village_location_aliases",
        sa.column("alias_text", sa.String()),
        sa.column("alias_normalized", sa.String()),
        sa.column("village_id", sa.Integer()),
        sa.column("note", sa.String()),
        sa.column("requires_geo_context", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    villages = sa.table(
        "villages",
        sa.column("id", sa.Integer()),
        sa.column("acs_code", sa.Integer()),
    )
    values_select = sa.values(
        alias_values.c.alias_text,
        alias_values.c.acs_code,
        alias_values.c.note,
        name="alias_values",
    ).data(ALIASES)
    select_stmt = sa.select(
        values_select.c.alias_text,
        values_select.c.alias_text.label("alias_normalized"),
        villages.c.id.label("village_id"),
        values_select.c.note,
        sa.false().label("requires_geo_context"),
        sa.true().label("is_active"),
    ).select_from(
        values_select.join(villages, villages.c.acs_code == values_select.c.acs_code)
    )
    insert_stmt = postgresql.insert(village_location_aliases).from_select(
        [
            "alias_text",
            "alias_normalized",
            "village_id",
            "note",
            "requires_geo_context",
            "is_active",
        ],
        select_stmt,
    )
    op.execute(
        insert_stmt.on_conflict_do_update(
            index_elements=["alias_normalized"],
            set_={
                "village_id": insert_stmt.excluded.village_id,
                "note": insert_stmt.excluded.note,
                "requires_geo_context": False,
                "is_active": True,
            },
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM village_location_aliases WHERE alias_normalized = ANY(:aliases)")
        .bindparams(sa.bindparam("aliases", [alias for alias, _acs_code, _note in ALIASES]))
    )
    op.drop_column("incidents", "village_display_name")
