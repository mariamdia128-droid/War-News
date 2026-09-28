"""Backfill stored casualty status from source text and incident counts.

Dry-run by default. This script never creates verification flags.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, select, update

from app.core.database import SessionLocal
from app.news.models import Incident, RawMessage, UpdateAction
from app.news.services.incident_details.casualty_status import (
    status_for_incident_row,
    target_location_count_from_extraction,
)
from app.news.services.incidents.incident_change_log import record_incident_change

OUT_CSV = Path(__file__).resolve().parent / "out" / "casualty_status_backfill_dryrun.csv"
STATUSES = (
    "none_mentioned",
    "explicit_none",
    "exact",
    "count_missing",
    "aggregate_only",
)


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _rows(db) -> tuple[list[dict[str, Any]], bool]:
    columns = {column["name"] for column in inspect(db.get_bind()).get_columns("incidents")}
    has_status = "casualty_status" in columns
    selected = [
        Incident.id.label("incident_id"),
        Incident.raw_message_id,
        Incident.village_id,
        Incident.deaths,
        Incident.injuries,
        Incident.total_deaths,
        Incident.total_injuries,
        Incident.verification_status,
        Incident.version,
        RawMessage.raw_text,
        RawMessage.extraction_result,
        RawMessage.match_result,
    ]
    if has_status:
        selected.extend(
            [
                Incident.casualty_status,
                Incident.casualty_is_preliminary,
                Incident.casualty_status_evidence,
            ]
        )
    query = (
        select(*selected)
        .select_from(Incident)
        .outerjoin(RawMessage, RawMessage.id == Incident.raw_message_id)
        .where(Incident.is_deleted.is_(False))
        .order_by(Incident.id)
    )
    rows = []
    for record in db.execute(query).mappings():
        row = dict(record)
        extraction = row.get("extraction_result") or {}
        row["extraction_payload"] = extraction if isinstance(extraction, dict) else {}
        row["target_location_count"] = target_location_count_from_extraction(
            row["extraction_payload"].get("village"),
            row["extraction_payload"].get("village_roles"),
            row["extraction_payload"].get("sub_events"),
        )
        row["derived"] = status_for_incident_row(
            row.get("raw_text") or "",
            row["extraction_payload"],
            {
                "deaths": row.get("deaths"),
                "injuries": row.get("injuries"),
                "total_deaths": row.get("total_deaths"),
                "total_injuries": row.get("total_injuries"),
            },
            target_location_count=row["target_location_count"],
            row_village_id=row.get("village_id"),
            match_result=row.get("match_result"),
        )
        rows.append(row)
    return rows, has_status


def _disagreements(row: dict[str, Any]) -> list[str]:
    derived = row["derived"]
    any_count = any(
        _int(row.get(field)) is not None
        for field in ("deaths", "injuries", "total_deaths", "total_injuries")
    )
    issues = []
    if derived.status == "exact" and not any_count:
        issues.append("derived_exact_but_row_counts_empty")
    if any_count and derived.status == "none_mentioned":
        issues.append("row_counts_present_but_no_casualty_mention")
    stored = row.get("casualty_status")
    if stored is not None and stored != derived.status:
        issues.append(f"stored_status_differs:{stored}->{derived.status}")
    return issues


def _write_csv(rows: list[dict[str, Any]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        "incident_id", "raw_message_id", "stored_status", "derived_status",
        "deaths_status", "injuries_status", "is_preliminary", "evidence",
        "deaths", "total_deaths", "injuries", "total_injuries", "disagreement",
    )
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            result = row["derived"]
            writer.writerow(
                {
                    "incident_id": row["incident_id"],
                    "raw_message_id": row["raw_message_id"],
                    "stored_status": row.get("casualty_status"),
                    "derived_status": result.status,
                    "deaths_status": result.deaths_status,
                    "injuries_status": result.injuries_status,
                    "is_preliminary": result.is_preliminary,
                    "evidence": result.evidence,
                    "deaths": row["deaths"],
                    "total_deaths": row["total_deaths"],
                    "injuries": row["injuries"],
                    "total_injuries": row["total_injuries"],
                    "disagreement": ";".join(_disagreements(row)),
                }
            )


def _report(rows: list[dict[str, Any]]) -> None:
    overall = Counter(row["derived"].status for row in rows)
    deaths = Counter(row["derived"].deaths_status for row in rows)
    injuries = Counter(row["derived"].injuries_status for row in rows)
    preliminary = sum(row["derived"].is_preliminary for row in rows)
    print(f"processed: {len(rows)}")
    print(f"overall: {dict((status, overall[status]) for status in STATUSES)}")
    print(f"deaths: {dict((status, deaths[status]) for status in STATUSES)}")
    print(f"injuries: {dict((status, injuries[status]) for status in STATUSES)}")
    print(f"preliminary: {preliminary}")
    print("examples (up to 5 per overall status):")
    by_status: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_status[row["derived"].status].append(row)
    for status in STATUSES:
        for row in by_status[status][:5]:
            print(
                f"  {status}: incident={row['incident_id']} message={row['raw_message_id']} "
                f"counts=({row['deaths']},{row['injuries']}) evidence={row['derived'].evidence!r}"
            )
    disagreements = [row for row in rows if _disagreements(row)]
    print(f"disagreements: {len(disagreements)}")
    for row in disagreements:
        print(
            f"  incident={row['incident_id']} message={row['raw_message_id']} "
            f"derived={row['derived'].status} counts=({row['deaths']},{row['injuries']}) "
            f"issues={','.join(_disagreements(row))}"
        )
    print(f"csv: {OUT_CSV}")


def _apply(rows: list[dict[str, Any]], db) -> dict[str, int]:
    processed = succeeded = failed = 0
    for row in rows:
        processed += 1
        result = row["derived"]
        before = {
            "casualty_status": row.get("casualty_status"),
            "casualty_is_preliminary": row.get("casualty_is_preliminary"),
            "casualty_status_evidence": row.get("casualty_status_evidence"),
        }
        after = {
            "casualty_status": result.status,
            "casualty_is_preliminary": result.is_preliminary,
            "casualty_status_evidence": result.evidence,
        }
        if before == after:
            succeeded += 1
            continue
        try:
            changed = db.execute(
                update(Incident)
                .where(
                    Incident.id == row["incident_id"],
                    Incident.version == row["version"],
                    Incident.casualty_status == before["casualty_status"],
                    Incident.casualty_is_preliminary == before["casualty_is_preliminary"],
                    Incident.casualty_status_evidence == before["casualty_status_evidence"],
                )
                .values(**after, version=Incident.version + 1)
            )
            if changed.rowcount != 1:
                failed += 1
                continue
            record_incident_change(
                db,
                incident_id=row["incident_id"],
                action=UpdateAction.pipeline_merge,
                old_values=before,
                new_values={**after, "casualty_status_backfill": True},
                performed_by=None,
            )
            succeeded += 1
        except Exception:
            failed += 1
    return {"processed": processed, "succeeded": succeeded, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write status fields in one transaction")
    args = parser.parse_args()

    with SessionLocal() as db:
        rows, has_status = _rows(db)
        if args.apply and not has_status:
            raise RuntimeError("Run the casualty status migration before --apply.")
        _write_csv(rows)
        _report(rows)
        if args.apply:
            db.rollback()
            with db.begin():
                print(f"apply: {_apply(rows, db)}")


if __name__ == "__main__":
    main()
