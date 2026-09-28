"""Preview or create deterministic casualty verification flags."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import inspect, select

from app.core.database import SessionLocal
from app.news.models import Incident, RawMessage
from app.news.repositories.incident_verification_flag_repository import IncidentVerificationFlagRepository
from app.news.services.casualty_flag_evaluator import CasualtyFlagEvaluator
from app.news.services.incident_details.casualty_text import find_count_mentions
from scripts.fixes.casualty_status_backfill import _rows as status_rows

OUT = Path(__file__).resolve().parent / "out" / "casualty_flags_backfill_dryrun.csv"


def candidates(db, since: date) -> tuple[list[dict], Counter]:
    skipped: Counter = Counter(); rows: list[dict] = []
    columns = {column["name"] for column in inspect(db.get_bind()).get_columns("incidents")}
    if "casualty_status" not in columns:
        derived_rows, _ = status_rows(db)
        for item in derived_rows:
            if item["created_at"].date() < since: continue
            result = item["derived"]
            reasons = []
            missing = [kind for kind in ("deaths", "injuries") if getattr(result, f"{kind}_status") == "count_missing"]
            if missing: reasons.append(("count_missing", f"{' and '.join(x.title() for x in missing)} reported but no exact number: «{result.evidence or ''}»"))
            if result.status == "aggregate_only" and any(isinstance(v, int) and v > 0 for v in result.remaining_total.values()):
                reasons.append(("aggregate_no_breakdown", "Aggregate casualty toll reported with no per-location breakdown"))
            if not reasons: skipped["status_not_flaggable"] += 1; continue
            for reason, summary in reasons:
                count_words = [m.rule for m in find_count_mentions(item.get("raw_text") or "") if m.rule in {"singular", "dual"}]
                rows.append({"incident_id": item["incident_id"], "source_message_id": item["raw_message_id"],
                             "event_day": item["created_at"].date(), "reason_code": reason,
                             "sentence": (result.evidence or item.get("raw_text") or "")[:320], "summary": summary,
                             "contains_singular_or_dual": bool(count_words)})
        return rows, skipped
    query = select(Incident, RawMessage.raw_text).outerjoin(RawMessage, RawMessage.id == Incident.raw_message_id).where(
        Incident.created_at >= datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc)
    ).order_by(Incident.created_at, Incident.id)
    repository = IncidentVerificationFlagRepository(db)
    for incident, text in db.execute(query):
        if incident.is_deleted or incident.verification_status == "rejected": skipped["removed_or_rejected"] += 1; continue
        reasons = []
        missing = [kind for kind in ("deaths", "injuries") if getattr(incident, f"casualty_{kind}_status") == "count_missing"]
        if missing: reasons.append(("count_missing", f"{' and '.join(x.title() for x in missing)} reported but no exact number: «{incident.casualty_status_evidence or ''}»"))
        remaining = incident.casualty_status_remaining_total or {}
        if incident.casualty_status == "aggregate_only" and any(isinstance(v, int) and v > 0 for v in remaining.values()):
            reasons.append(("aggregate_no_breakdown", "Aggregate casualty toll reported with no per-location breakdown"))
        if not reasons: skipped["status_not_flaggable"] += 1; continue
        for reason, summary in reasons:
            if repository.has_previously_reviewed(incident.id, reason): skipped["previously_reviewed"] += 1; continue
            count_words = [m.rule for m in find_count_mentions(text or "") if m.rule in {"singular", "dual"}]
            rows.append({"incident_id": incident.id, "source_message_id": incident.raw_message_id,
                         "event_day": incident.created_at.date(), "reason_code": reason,
                         "sentence": (incident.casualty_status_evidence or text or "")[:320], "summary": summary,
                         "contains_singular_or_dual": bool(count_words)})
    return rows, skipped


def write(rows: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys() if rows else ("incident_id", "source_message_id", "event_day", "reason_code", "sentence", "summary", "contains_singular_or_dual"))
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", type=date.fromisoformat, default=date.today() - timedelta(days=14))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        rows, skipped = candidates(db, args.since); write(rows)
        by_reason = Counter(row["reason_code"] for row in rows); by_day = Counter(row["event_day"] for row in rows)
        print(f"processed: {len(rows) + sum(skipped.values())}"); print(f"would_create: {dict(by_reason)}")
        for reason in sorted(by_reason):
            for row in [r for r in rows if r["reason_code"] == reason][:5]:
                print(f"  {reason}: incident={row['incident_id']} message={row['source_message_id']} sentence={row['sentence']!r} summary={row['summary']!r}")
        print(f"per_day: {dict(sorted(by_day.items()))}"); print(f"peak_per_day: {max(by_day.values(), default=0)}")
        print(f"skipped: {dict(skipped)}")
        violations = [row for row in rows if row["reason_code"] == "count_missing" and row["contains_singular_or_dual"]]
        print(f"count_missing_with_singular_or_dual: {len(violations)}")
        print(f"csv: {OUT}")
        if args.apply:
            db.rollback(); stats = {"processed": 0, "succeeded": 0, "failed": 0}
            with db.begin():
                evaluator = CasualtyFlagEvaluator(db, enabled=True)
                for incident_id in dict.fromkeys(row["incident_id"] for row in rows):
                    stats["processed"] += 1
                    try: evaluator.evaluate_incident(incident_id); stats["succeeded"] += 1
                    except Exception: stats["failed"] += 1
            print(f"apply: {stats}")


if __name__ == "__main__": main()
