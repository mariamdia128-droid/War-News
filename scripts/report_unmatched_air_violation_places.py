#!/usr/bin/env python
"""List the place names on air-violation rows that resolved to no village.

Read-only. Never writes. The point is a batch of alias candidates: run it,
look at the grouped names, and add the real ones through the
``village_location_aliases`` migration route (see
``alembic/migration/20261001_0074_add_bazourieh_village_aliases.py`` for the
shape, and ``Data/VillageLocationAliases.json`` for the seed list).

A name is reported only when the row has no resolved village AND no caza, so
the 314 rows that legitimately carry a region designation are not listed.

    docker compose exec backend python scripts/report_unmatched_air_violation_places.py
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from app.core.config import settings
from app.core.text_normalization import village_match_key
from app.news.services.air_violations.air_violation_eligibility import (
    GENERIC_DIRECTION_REASON,
    UNMATCHED_LOCATION_REASON,
    evaluate_air_violation_location,
    evaluate_air_violation_text,
)


def _session() -> Session:
    url = os.environ.get("DATABASE_URL", settings.database_url)
    if "@db:" in url and not Path("/.dockerenv").exists():
        url = url.replace("@db:5432", f"@localhost:{os.environ.get('POSTGRES_HOST_PORT', '5432')}")
    return sessionmaker(bind=create_engine(url))()


FETCH_SQL = """
    SELECT av.id,
           av.condition_id,
           av.caza_en,
           av.caza_ar,
           COALESCE(s.name, r.source_name, 'Unknown source') AS source,
           CONCAT_WS(E'\n', NULLIF(r.raw_text, ''), NULLIF(av.khabar, '')) AS source_text,
           (
               SELECT COUNT(*) FROM air_violation_locations l
               WHERE l.air_violation_id = av.id
           ) AS location_count,
           av.village_id,
           (
               SELECT string_agg(DISTINCT vm->>'raw_village_text', ' | ')
               FROM jsonb_array_elements(
                   COALESCE(r.match_result::jsonb -> 'village_matches', '[]'::jsonb)
               ) AS vm
               WHERE vm->>'matched_village_id' IS NULL
                 AND NULLIF(vm->>'raw_village_text', '') IS NOT NULL
           ) AS extractor_names,
           (
               r.raw_payload ? 'ocr_text'
               OR COALESCE(r.raw_text, '') LIKE '%__RED_ZONE_TEXT__%'
           ) AS is_ocr
    FROM air_violations av
    LEFT JOIN raw_messages r ON r.id = av.raw_message_id
    LEFT JOIN sources s ON s.id = av.source_id
    ORDER BY av.id
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Group the unmatched place names on placeless air-violation rows",
    )
    parser.add_argument(
        "--limit-rows", type=int, default=6,
        help="rows to print under each name (default 6)",
    )
    args = parser.parse_args()

    db = _session()
    try:
        rows = db.execute(text(FETCH_SQL)).mappings().all()
        known_keys = {
            village_match_key(name)
            for (name,) in db.execute(text(
                "SELECT ref_name_ar FROM villages WHERE ref_name_ar IS NOT NULL"
            )).all()
            if name
        }
        known_keys |= {
            village_match_key(name)
            for row in db.execute(text(
                "SELECT acs_name, cad_name, ref_name_en FROM villages"
            )).all()
            for name in row
            if name
        }
        known_keys |= {
            village_match_key(alias)
            for (alias,) in db.execute(text(
                "SELECT alias_text FROM village_location_aliases WHERE is_active"
            )).all()
            if alias
        }
    finally:
        db.close()

    by_name: dict[str, list[dict[str, object]]] = defaultdict(list)
    generic: list[int] = []
    ocr_rows: list[int] = []
    decided_by_text: dict[str, list[int]] = defaultdict(list)
    placed = 0
    for row in rows:
        # The text rules come first in every entry point, so a row they
        # already decide is not a location question and contributes no alias
        # candidate. Without this, the words of a rejected UNIFIL attribution
        # read as place names.
        text_result = evaluate_air_violation_text(row["source_text"])
        if not text_result.eligible:
            decided_by_text[text_result.reason].append(int(row["id"]))
            continue
        has_village = row["village_id"] is not None or (row["location_count"] or 0) > 0
        extractor_names = tuple(
            part.strip()
            for part in (row["extractor_names"] or "").split("|")
            if part.strip()
        )
        result = evaluate_air_violation_location(
            row["source_text"],
            has_resolved_village=has_village,
            caza_label=row["caza_en"] or row["caza_ar"],
            unmatched_names=extractor_names,
        )
        if result.eligible:
            placed += 1
            continue
        if result.reason == GENERIC_DIRECTION_REASON:
            generic.append(int(row["id"]))
            continue
        if result.reason != UNMATCHED_LOCATION_REASON:
            continue
        if row["is_ocr"]:
            # An image alert whose OCR did not resolve. The leftovers are
            # scanner noise, not place names, so these are counted and left
            # out of the alias candidates.
            ocr_rows.append(int(row["id"]))
            continue
        for name in result.matched_terms:
            if len(name) < 3:
                continue
            by_name[name].append({
                "id": int(row["id"]),
                "condition_id": row["condition_id"],
                "source": row["source"],
                "text": " ".join((row["source_text"] or "").split())[:120],
            })

    print("=== unmatched air-violation place names (read-only) ===")
    print(f"rows scanned: {len(rows)}")
    print(f"rows with a village or a recognised region: {placed}")
    print(f"rows with no location at all ({GENERIC_DIRECTION_REASON}): {len(generic)}")
    if generic:
        print(f"  ids: {generic}")
    for reason, ids in sorted(decided_by_text.items()):
        print(f"rows already decided by the text rules ({reason}): {len(ids)}")
        print(f"  ids: {ids[:20]}{' ...' if len(ids) > 20 else ''}")
    print(f"rows from unresolved image alerts (OCR noise, no candidates): {len(ocr_rows)}")
    if ocr_rows:
        print(f"  ids: {ocr_rows}")
    print(f"distinct unmatched names: {len(by_name)}")
    print()

    if not by_name:
        print("No unmatched place names. Nothing to add.")
        return

    print(f"{'count':>5}  {'new?':<5}  name")
    print("-" * 60)
    for name, entries in sorted(by_name.items(), key=lambda item: (-len(item[1]), item[0])):
        is_new = "yes" if village_match_key(name) not in known_keys else "known"
        print(f"{len(entries):>5}  {is_new:<5}  {name}")
        for entry in entries[: args.limit_rows]:
            print(f"         id={entry['id']} cond={entry['condition_id']}"
                  f" src={entry['source']} :: {entry['text']}")
        if len(entries) > args.limit_rows:
            print(f"         ... and {len(entries) - args.limit_rows} more")
    print()
    print("'known' means the name already resolves through villages or an active")
    print("alias, so that row failed for another reason and needs a closer look.")
    print("Read-only: nothing was written.")


if __name__ == "__main__":
    main()
