#!/usr/bin/env python
"""Backfill stored window IDs for historical air-violation rows.

Dry-run is the default. Use ``--apply`` only after reviewing the output.

Usage:
  python scripts/backfill_air_violation_windows.py
  python scripts/backfill_air_violation_windows.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

from app.news.services.air_violations.caza_alias_resolver import canonicalize_caza
from app.news.services.air_violations.window_grouping_service import (
    AirViolationWindowInput,
    assign_air_violation_window_ids,
)

DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:secret@localhost:5432/war_news_dev"
BATCH_SIZE = 100


def _session() -> Session:
    url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    if "@db:" in url and not Path("/.dockerenv").exists():
        url = url.replace("@db:", "@localhost:")
    return sessionmaker(bind=create_engine(url))()


@dataclass(frozen=True)
class AirViolationRow:
    id: int
    caza_en: str | None
    caza_ar: str | None
    village_caza_en: str | None
    village_caza_ar: str | None
    location_cazas_en: tuple[str, ...]
    location_cazas_ar: tuple[str, ...]
    event_date: date
    event_time: time | None
    current_window_id: str | None


@dataclass(frozen=True)
class WindowPlan:
    air_violation_id: int
    current_window_id: str | None
    proposed_window_id: str | None
    caza: str | None
    resolution_source: str


def _has_column(db: Session, column_name: str) -> bool:
    return column_name in {
        column["name"]
        for column in inspect(db.get_bind()).get_columns("air_violations")
    }


def fetch_rows(db: Session) -> list[AirViolationRow]:
    window_expr = (
        "av.window_id AS window_id"
        if _has_column(db, "window_id")
        else "NULL::text AS window_id"
    )
    rows = db.execute(
        text(
            f"""
            SELECT
              av.id,
              av.caza_en,
              av.caza_ar,
              primary_village.caza_en AS village_caza_en,
              primary_village.caza_ar AS village_caza_ar,
              COALESCE(
                ARRAY_AGG(DISTINCT location_village.caza_en)
                  FILTER (WHERE location_village.caza_en IS NOT NULL),
                ARRAY[]::varchar[]
              ) AS location_cazas_en,
              COALESCE(
                ARRAY_AGG(DISTINCT location_village.caza_ar)
                  FILTER (WHERE location_village.caza_ar IS NOT NULL),
                ARRAY[]::varchar[]
              ) AS location_cazas_ar,
              av.event_date,
              av.event_time,
              {window_expr}
            FROM air_violations av
            LEFT JOIN villages primary_village ON primary_village.id = av.village_id
            LEFT JOIN air_violation_locations avl ON avl.air_violation_id = av.id
            LEFT JOIN villages location_village ON location_village.id = avl.village_id
            GROUP BY
              av.id,
              primary_village.caza_en,
              primary_village.caza_ar
            ORDER BY av.event_date ASC, av.event_time ASC NULLS FIRST, av.id ASC
            """
        )
    ).mappings().all()
    return [
        AirViolationRow(
            id=int(row["id"]),
            caza_en=row["caza_en"],
            caza_ar=row["caza_ar"],
            village_caza_en=row["village_caza_en"],
            village_caza_ar=row["village_caza_ar"],
            location_cazas_en=tuple(row["location_cazas_en"] or ()),
            location_cazas_ar=tuple(row["location_cazas_ar"] or ()),
            event_date=row["event_date"],
            event_time=row["event_time"],
            current_window_id=row["window_id"],
        )
        for row in rows
    ]


def _is_multiple_regions(value: str | None) -> bool:
    return (value or "").strip().casefold() == "multiple regions"


def _canonical_location_cazas(row: AirViolationRow) -> set[str]:
    return {
        caza
        for value in (*row.location_cazas_en, *row.location_cazas_ar)
        if (caza := canonicalize_caza(value))
    }


def resolve_row_caza(row: AirViolationRow) -> tuple[str | None, str]:
    village_caza = canonicalize_caza(row.village_caza_en) or canonicalize_caza(
        row.village_caza_ar
    )
    if village_caza:
        return village_caza, "village_id"

    location_cazas = _canonical_location_cazas(row)
    if len(location_cazas) == 1:
        return next(iter(location_cazas)), "air_violation_locations"
    if len(location_cazas) > 1:
        return None, "ambiguous_air_violation_locations"

    if _is_multiple_regions(row.caza_en):
        return None, "multiple_regions_without_locations"

    raw_caza = canonicalize_caza(row.caza_en) or canonicalize_caza(row.caza_ar)
    return raw_caza, "raw_caza" if raw_caza else "unresolved"


def build_plans(rows: list[AirViolationRow]) -> list[WindowPlan]:
    resolved = {row.id: resolve_row_caza(row) for row in rows}
    inputs = [
        AirViolationWindowInput(
            id=row.id,
            caza_en=resolved[row.id][0],
            caza_ar=None,
            event_date=row.event_date,
            event_time=row.event_time,
        )
        for row in rows
        if resolved[row.id][0]
    ]
    assignments = assign_air_violation_window_ids(inputs)
    return [
        WindowPlan(
            air_violation_id=row.id,
            current_window_id=row.current_window_id,
            proposed_window_id=assignments.get(row.id),
            caza=resolved[row.id][0],
            resolution_source=resolved[row.id][1],
        )
        for row in rows
    ]


def print_dry_run(plans: list[WindowPlan], examples: int) -> None:
    tagged = [plan for plan in plans if plan.proposed_window_id]
    unresolved = [plan for plan in plans if not plan.proposed_window_id]
    changes = [
        plan for plan in tagged
        if plan.current_window_id != plan.proposed_window_id
    ]
    noops = [
        plan for plan in tagged
        if plan.current_window_id == plan.proposed_window_id
    ]
    by_caza = Counter(plan.caza or "(unresolved)" for plan in plans)
    by_source = Counter(plan.resolution_source for plan in plans)
    by_window: dict[str, int] = defaultdict(int)
    for plan in tagged:
        by_window[plan.proposed_window_id or ""] += 1

    print("=== air violation window tagging backfill (dry run) ===")
    print(f"rows scanned: {len(plans)}")
    print(f"rows with proposed window_id: {len(tagged)}")
    print(f"rows left untagged (unresolved caza): {len(unresolved)}")
    print(f"windows that would exist: {len(by_window)}")
    print(f"rows that would change: {len(changes)}")
    print(f"rows already correctly tagged/no-op: {len(noops)}")

    print("\nCaza breakdown:")
    for caza, count in by_caza.most_common():
        print(f"  {caza}: {count}")

    print("\nResolution source breakdown:")
    for source, count in by_source.most_common():
        print(f"  {source}: {count}")

    print(f"\nWindow examples (up to {examples}):")
    for window_id, count in list(sorted(by_window.items()))[:examples]:
        print(f"  {window_id}: {count} rows")

    print(f"\nUntagged examples (up to {examples}):")
    for plan in unresolved[:examples]:
        print(f"  air_violation_id={plan.air_violation_id}")


def apply_plans(db: Session, plans: list[WindowPlan]) -> dict[str, int]:
    if not _has_column(db, "window_id"):
        raise RuntimeError("air_violations.window_id does not exist. Run the migration first.")
    candidates = [
        plan for plan in plans
        if plan.proposed_window_id and plan.current_window_id != plan.proposed_window_id
    ]
    updated = failed = 0
    for index in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[index:index + BATCH_SIZE]
        try:
            for plan in batch:
                result = db.execute(
                    text(
                        """
                        UPDATE air_violations
                        SET window_id = :window_id
                        WHERE id = :id
                          AND (window_id IS DISTINCT FROM :window_id)
                        """
                    ),
                    {"id": plan.air_violation_id, "window_id": plan.proposed_window_id},
                )
                updated += result.rowcount or 0
            db.commit()
        except Exception:
            db.rollback()
            failed += len(batch)
            raise
    return {"processed": len(candidates), "updated": updated, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run or apply historical air-violation window_id tagging."
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--examples", type=int, default=8)
    args = parser.parse_args()

    db = _session()
    try:
        plans = build_plans(fetch_rows(db))
        print_dry_run(plans, examples=max(1, args.examples))
        if not args.apply:
            print("\nDry run only - no database writes. Re-run with --apply after Najdi review.")
            return

        stats = apply_plans(db, plans)
        print("\nApplied:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
