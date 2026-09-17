#!/usr/bin/env python
"""Flag historical air-violation rows for review under new exclusion rules.

Dry-run is the default. Use ``--apply`` only after reviewing the output.

Usage:
  python scripts/backfill_air_violation_exclusion_review.py
  python scripts/backfill_air_violation_exclusion_review.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

from app.news.services.air_violations.air_violation_exclusions import air_violation_exclusion

DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:secret@localhost:5432/war_news_dev"
BATCH_SIZE = 100
FLAGGED_STATUS = "flagged_for_review"


def _session() -> Session:
    url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    if "@db:" in url and not Path("/.dockerenv").exists():
        url = url.replace("@db:", "@localhost:")
    return sessionmaker(bind=create_engine(url))()


@dataclass(frozen=True)
class AirViolationTextRow:
    id: int
    khabar: str
    source_text: str
    current_review_status: str | None
    current_review_reason: str | None


@dataclass(frozen=True)
class ReviewPlan:
    air_violation_id: int
    reason: str
    evidence_span: str
    source_excerpt: str
    current_review_status: str | None
    current_review_reason: str | None


def _has_column(db: Session, column_name: str) -> bool:
    return column_name in {
        column["name"]
        for column in inspect(db.get_bind()).get_columns("air_violations")
    }


def fetch_rows(db: Session) -> list[AirViolationTextRow]:
    status_expr = "av.review_status" if _has_column(db, "review_status") else "NULL::text AS review_status"
    reason_expr = "av.review_reason" if _has_column(db, "review_reason") else "NULL::text AS review_reason"
    rows = db.execute(
        text(
            f"""
            SELECT
              av.id,
              av.khabar,
              CONCAT_WS(E'\n',
                NULLIF(r.raw_text, ''),
                NULLIF(r.raw_payload #>> '{{enrichment,text}}', ''),
                NULLIF(av.khabar, '')
              ) AS source_text,
              {status_expr},
              {reason_expr}
            FROM air_violations av
            LEFT JOIN raw_messages r ON r.id = av.raw_message_id
            ORDER BY av.id ASC
            """
        )
    ).mappings().all()
    return [
        AirViolationTextRow(
            id=int(row["id"]),
            khabar=row["khabar"],
            source_text=row["source_text"] or row["khabar"],
            current_review_status=row["review_status"],
            current_review_reason=row["review_reason"],
        )
        for row in rows
    ]


def _excerpt(text_value: str, evidence_span: str) -> str:
    index = text_value.find(evidence_span)
    if index < 0:
        return text_value[:160].replace("\n", " ").strip()
    start = max(0, index - 60)
    end = min(len(text_value), index + len(evidence_span) + 80)
    return text_value[start:end].replace("\n", " ").strip()


def build_plans(rows: list[AirViolationTextRow]) -> list[ReviewPlan]:
    plans: list[ReviewPlan] = []
    for row in rows:
        exclusion = air_violation_exclusion(row.source_text)
        if exclusion is None:
            continue
        plans.append(
            ReviewPlan(
                air_violation_id=row.id,
                reason=exclusion.reason,
                evidence_span=exclusion.evidence_span,
                source_excerpt=_excerpt(row.source_text, exclusion.evidence_span),
                current_review_status=row.current_review_status,
                current_review_reason=row.current_review_reason,
            )
        )
    return plans


def print_dry_run(total_rows: int, plans: list[ReviewPlan], examples: int) -> None:
    counts = Counter(plan.reason for plan in plans)
    changes = [
        plan for plan in plans
        if plan.current_review_status != FLAGGED_STATUS
        or plan.current_review_reason != plan.reason
    ]
    noops = [plan for plan in plans if plan not in changes]

    print("=== air violation exclusion review backfill (dry run) ===")
    print(f"rows scanned: {total_rows}")
    print(f"rows that would be flagged: {len(plans)}")
    print(f"rows that would change: {len(changes)}")
    print(f"rows already correctly flagged/no-op: {len(noops)}")

    print("\nBy reason:")
    for reason, count in counts.most_common():
        print(f"  {reason}: {count}")

    print(f"\nExamples (up to {examples}):")
    for plan in plans[:examples]:
        print(
            f"  air_violation_id={plan.air_violation_id} reason={plan.reason}\n"
            f"    evidence={plan.evidence_span!r}\n"
            f"    snippet={plan.source_excerpt!r}"
        )


def apply_plans(db: Session, plans: list[ReviewPlan]) -> dict[str, int]:
    if not _has_column(db, "review_status") or not _has_column(db, "review_reason"):
        raise RuntimeError(
            "air_violations.review_status/review_reason do not exist. Run the migration first."
        )
    candidates = [
        plan for plan in plans
        if plan.current_review_status != FLAGGED_STATUS
        or plan.current_review_reason != plan.reason
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
                        SET review_status = :status,
                            review_reason = :reason
                        WHERE id = :id
                          AND (
                            review_status IS DISTINCT FROM :status
                            OR review_reason IS DISTINCT FROM :reason
                          )
                        """
                    ),
                    {
                        "id": plan.air_violation_id,
                        "status": FLAGGED_STATUS,
                        "reason": plan.reason,
                    },
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
        description="Dry-run or apply historical air-violation exclusion review flags."
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--examples", type=int, default=8)
    args = parser.parse_args()

    db = _session()
    try:
        rows = fetch_rows(db)
        plans = build_plans(rows)
        print_dry_run(len(rows), plans, examples=max(1, args.examples))
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
