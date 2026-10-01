#!/usr/bin/env python
"""Audit and optionally backfill the final air-violation rules.

Dry-run is the default. It always refreshes the CSV and manual-review SQL
artifacts, but never changes the database. ``--apply`` updates only reversible
classification/review/window/war-month fields; ineligible rows are never
deleted here.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from app.core.config import settings
from app.core.text_normalization import normalize_arabic_text
from app.news.services.air_violations.air_violation_eligibility import (
    EligibilityResult,
    evaluate_air_violation_text,
)
from app.news.services.air_violations.war_month import war_month
from scripts.backfill_air_violation_windows import build_plans as build_window_plans
from scripts.backfill_air_violation_windows import fetch_rows as fetch_window_rows

OUTPUT_DIR = PROJECT_ROOT / "scripts" / "sql"
REVIEW_CSV = OUTPUT_DIR / "air_violations_reject_review.csv"
MOVE_SQL = OUTPUT_DIR / "air_violations_move_to_incidents.sql"
BATCH_SIZE = 100

DRONE_TERMS = ("طيران مسير", "مسير", "مسيره", "مسيرة", "درون", "drone", "uav")
HELICOPTER_TERMS = ("طيران مروحي", "مروحي", "مروحيه", "هليكوبتر", "helicopter")
FLIGHT_TERMS = ("تحلق", "يحلق", "تحليق", "تحوم", "تحويم", "حلقت", "hover", "flying")
FIRE_TERMS = ("حريق", "احتراق")
# A correction post ("ordinary fire, there was no strike") trips the kinetic
# terms while denying them. Those rows go to a human, not to the incident move.
CLARIFICATION_TERMS = (
    "لا يوجد", "لا توجد", "ليس هناك", "لا صحة", "نفي", "اقتضى التوضيح", "للتوضيح", "عادي",
)
LEGACY_AUDIT_RE = re.compile(
    r"(?:غارة(?! وهمية)|غارات(?! وهمية)|اغار|أغار|قصف جوي|قصف مدفعي|قذائف|مدفعية|صواريخ|صاروخ|انفجار|اشتباكات?|تمشيط|رشقات نارية|شهداء|شهيد|جرحى|إصابات)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Row:
    id: int
    raw_message_id: int | None
    condition_id: int
    condition: str
    source: str
    event_date: date
    source_text: str
    review_status: str | None
    review_reason: str | None
    current_war_month: int | None


@dataclass(frozen=True)
class Plan:
    row: Row
    eligibility: EligibilityResult
    proposed_condition_id: int | None
    review_reason: str | None
    proposed_war_month: int
    review_only: bool = False

    @property
    def moves_to_incidents(self) -> bool:
        """Ineligible, and a real event rather than a notice, tag or blank row.

        Only kinetic/casualty/damage rows describe something that belongs in
        the incident pipeline. Every other exclusion (end-of-day digests,
        channel housekeeping, bare hashtags, UNIFIL flights, empty text) goes
        to a human instead of being pushed through as an incident.
        """
        return self.eligibility.belongs_in_incidents and not self.review_only


def _session() -> Session:
    url = os.environ.get("DATABASE_URL", settings.database_url)
    if "@db:" in url and not Path("/.dockerenv").exists():
        url = url.replace("@db:5432", f"@localhost:{os.environ.get('POSTGRES_HOST_PORT', '5432')}")
    return sessionmaker(bind=create_engine(url))()


def _has_column(db: Session, name: str) -> bool:
    return name in {column["name"] for column in inspect(db.get_bind()).get_columns("air_violations")}


def fetch_rows(db: Session) -> list[Row]:
    war_expr = "av.war_month" if _has_column(db, "war_month") else "NULL::integer"
    rows = db.execute(text(f"""
        SELECT av.id, av.raw_message_id, av.condition_id,
               COALESCE(c.action_en, av.condition_id::text) AS condition,
               COALESCE(s.name, r.source_name, 'Unknown source') AS source,
               av.event_date, av.review_status, av.review_reason,
               {war_expr} AS current_war_month,
               CONCAT_WS(E'\n', NULLIF(r.raw_text, ''),
                 NULLIF(r.raw_payload #>> '{{enrichment,text}}', ''),
                 NULLIF(av.khabar, '')) AS source_text
        FROM air_violations av
        LEFT JOIN raw_messages r ON r.id = av.raw_message_id
        LEFT JOIN conditions c ON c.id = av.condition_id
        LEFT JOIN sources s ON s.id = av.source_id
        ORDER BY av.id
    """)).mappings().all()
    return [Row(
        id=int(row["id"]), raw_message_id=row["raw_message_id"],
        condition_id=int(row["condition_id"]), condition=row["condition"],
        source=row["source"], event_date=row["event_date"],
        source_text=row["source_text"] or "", review_status=row["review_status"],
        review_reason=row["review_reason"], current_war_month=row["current_war_month"],
    ) for row in rows]


def _contains(normalized: str, terms: tuple[str, ...]) -> bool:
    return any(normalize_arabic_text(term).casefold() in normalized for term in terms)


def build_plans(rows: list[Row]) -> list[Plan]:
    plans: list[Plan] = []
    for row in rows:
        eligibility = evaluate_air_violation_text(row.source_text)
        normalized = normalize_arabic_text(row.source_text).casefold()
        proposed_condition = 36 if row.condition_id == 38 and _contains(normalized, DRONE_TERMS) else None
        review_reason = None
        review_only = False
        if row.condition_id == 38 and _contains(normalized, HELICOPTER_TERMS) and not _contains(normalized, FLIGHT_TERMS):
            review_reason = "helicopter_without_hover_language"
            review_only = True
        if _contains(normalized, FIRE_TERMS) and (
            eligibility.eligible or _contains(normalized, CLARIFICATION_TERMS)
        ):
            review_reason = "ordinary_fire_requires_manual_review"
            review_only = True
        elif not eligibility.eligible:
            review_reason = eligibility.reason
            review_only = not eligibility.belongs_in_incidents
        plans.append(Plan(
            row, eligibility, proposed_condition, review_reason,
            war_month(row.event_date), review_only,
        ))
    return plans


def write_review_files(plans: list[Plan]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ineligible = [plan for plan in plans if plan.moves_to_incidents]
    with REVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "condition", "source", "text_excerpt", "matched_terms", "confidence"])
        for plan in ineligible:
            writer.writerow([
                plan.row.id, plan.row.condition, plan.row.source,
                " ".join(plan.row.source_text.split())[:160],
                " | ".join(plan.eligibility.matched_terms), 1.0,
            ])

    # A row with no raw_message_id (an Excel/Khabar import) has no message to
    # re-queue, so deleting it would drop the record with nothing taking its
    # place. Those are listed for a manual decision instead.
    movable = [plan for plan in ineligible if plan.row.raw_message_id]
    orphans = [plan for plan in ineligible if not plan.row.raw_message_id]

    lines = [
        "-- GENERATED REVIEW FILE. Inspect the CSV before running this file.",
        "-- Moves each approved row back to the incident pipeline exactly once.",
        "--",
        "-- RUN THIS ONLY AFTER the backfill has run with --apply: each DELETE is",
        "-- guarded on the review_status/review_reason that --apply writes, so on an",
        "-- un-applied database every DELETE matches zero rows.",
        "--",
        "-- Messages already 'materialized' or 'duplicate' are left untouched: they",
        "-- are represented by a live incident or by their canonical message, and",
        "-- reopening them is what would create a duplicate incident.",
        "--",
        "-- Re-queued rows go to 'parsed', not 'pending': they keep their",
        "-- filter_result, and the relevance stage only claims pending rows whose",
        "-- filter_result IS NULL, so 'pending' would strand them in no stage.",
        f"-- {len(movable)} rows are moved here; {len(orphans)} import rows have no",
        "-- source message and are listed, not deleted, at the end of this file.",
        "BEGIN;",
    ]
    for plan in movable:
        sql_reason = plan.eligibility.reason.replace("'", "''")
        lines.extend([
            f"-- air_violation_id={plan.row.id} reason={plan.eligibility.reason}",
            "UPDATE raw_messages rm",
            # 'parsed', not 'pending': these rows keep their filter_result, and
            # the relevance stage only claims pending rows whose filter_result
            # IS NULL, so a pending row is claimed by no stage at all. 'parsed'
            # feeds pre-dedup/extraction without an extraction_result, and
            # matching with one.
            "SET status = 'parsed'::message_status,",
            "    match_result = NULL,",
            "    error_message = NULL, processing_claim_stage = NULL,",
            "    processing_claimed_at = NULL, processing_claimed_by = NULL",
            f"WHERE rm.id = (SELECT raw_message_id FROM air_violations WHERE id = {plan.row.id})",
            "  AND rm.status NOT IN ('materialized'::message_status, 'duplicate'::message_status)",
            "  AND NOT EXISTS (SELECT 1 FROM incidents i",
            "                  WHERE i.raw_message_id = rm.id AND i.is_deleted = false);",
            f"DELETE FROM air_violations WHERE id = {plan.row.id}",
            f"  AND review_status = 'flagged_for_review' AND review_reason = '{sql_reason}';",
        ])
    lines.extend(["-- COMMIT only after checking affected row counts.", "COMMIT;", ""])
    if orphans:
        lines.append("-- Imported rows with no source message. Decide each one by hand:")
        for plan in orphans:
            excerpt = " ".join(plan.row.source_text.split())[:110].replace("\n", " ")
            lines.append(f"--   id={plan.row.id} condition={plan.row.condition} :: {excerpt}")
        lines.append("")
    MOVE_SQL.write_text("\n".join(lines), encoding="utf-8")


def apply_plans(db: Session, plans: list[Plan], window_plans: list[object]) -> dict[str, int]:
    if not _has_column(db, "war_month"):
        raise RuntimeError("air_violations.war_month is missing; run the generated migration first")
    processed = succeeded = failed = 0
    window_by_id = {plan.air_violation_id: plan.proposed_window_id for plan in window_plans}
    for start in range(0, len(plans), BATCH_SIZE):
        batch = plans[start:start + BATCH_SIZE]
        processed += len(batch)
        try:
            for plan in batch:
                db.execute(text("""
                    UPDATE air_violations
                    SET condition_id = COALESCE(:condition_id, condition_id),
                        review_status = CASE WHEN :reason IS NULL THEN review_status ELSE 'flagged_for_review' END,
                        review_reason = COALESCE(:reason, review_reason),
                        window_id = :window_id,
                        war_month = :war_month
                    WHERE id = :id
                """), {
                    "id": plan.row.id, "condition_id": plan.proposed_condition_id,
                    "reason": plan.review_reason, "window_id": window_by_id.get(plan.row.id),
                    "war_month": plan.proposed_war_month,
                })
            db.commit()
            succeeded += len(batch)
        except Exception:
            db.rollback()
            failed += len(batch)
    return {"processed": processed, "succeeded": succeeded, "failed": failed}


def _print_sample(title: str, plans: list[Plan], limit: int = 25) -> None:
    print(f"\n{title} (up to {limit}):")
    if not plans:
        print("  none")
    step = max(1, len(plans) // limit)
    for plan in plans[::step][:limit]:
        print(f"  id={plan.row.id} condition={plan.row.condition_id} text={' '.join(plan.row.source_text.split())[:160]!r}")


def _print_known_audit(plans: list[Plan]) -> None:
    by_id = {plan.row.id: plan for plan in plans}
    print("\nKnown audit verification:")
    for row_id in (747, 754, 866, 877, 1424, 1465, 1466, 1467, 1468):
        plan = by_id.get(row_id)
        if plan is None:
            print(f"  id={row_id}: missing")
            continue
        outcome = (
            "ineligible"
            if plan.moves_to_incidents
            else f"review:{plan.review_reason}"
            if plan.review_reason
            else "kept"
        )
        print(f"  id={row_id}: {outcome}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit/backfill final air-violation rules")
    parser.add_argument("--apply", action="store_true", help="write reversible field updates")
    args = parser.parse_args()
    db = _session()
    try:
        rows = fetch_rows(db)
        plans = build_plans(rows)
        window_plans = build_window_plans(fetch_window_rows(db))
        write_review_files(plans)
        ineligible = [plan for plan in plans if plan.moves_to_incidents]
        kept = [plan for plan in plans if plan.eligibility.eligible]
        category_changes = Counter(
            f"{plan.row.condition_id}->{plan.proposed_condition_id}"
            for plan in plans if plan.proposed_condition_id is not None
        )
        legacy_candidates = [
            plan for plan in plans if LEGACY_AUDIT_RE.search(plan.row.source_text)
        ]
        legacy_remaining = [
            plan for plan in legacy_candidates if plan.moves_to_incidents
        ]
        review_only = [plan for plan in plans if plan.review_only]
        print("=== consolidated air violation rules backfill ===")
        print(f"mode: {'APPLY' if args.apply else 'DRY RUN'}")
        print(f"rows scanned: {len(rows)}")
        print(f"rows ineligible (proposed for the incident move): {len(ineligible)}")
        print(f"rows held for review instead of moving: {len(review_only)}")
        print(f"category changes by type: {dict(category_changes)}")
        print(f"windows rebuilt: {len({plan.proposed_window_id for plan in window_plans if plan.proposed_window_id})}")
        print(f"war_month values set: {sum(plan.row.current_war_month != plan.proposed_war_month for plan in plans)}")
        print(f"review-needed count: {sum(plan.review_reason is not None for plan in plans)}")
        print(f"earlier-audit candidates reproduced: {len(legacy_candidates)}")
        print(f"earlier-audit candidates remaining ineligible: {len(legacy_remaining)}")
        print(f"earlier-audit false positives removed: {len(legacy_candidates) - len(legacy_remaining)}")
        _print_sample("Ineligible sample", ineligible)
        _print_sample("Kept sample", kept)
        _print_known_audit(plans)
        if args.apply:
            print(f"\nsummary: {apply_plans(db, plans, window_plans)}")
        else:
            print(f"\nsummary: {{'processed': {len(plans)}, 'succeeded': {len(plans)}, 'failed': 0}}")
            print("Dry run only: database unchanged. Review CSV and SQL were refreshed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
