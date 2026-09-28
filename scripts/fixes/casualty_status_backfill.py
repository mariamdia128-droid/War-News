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
from app.news.models import Incident, IncidentUpdate, RawMessage, UpdateAction
from app.news.services.incident_details.casualty_merge_guard import guard_casualty_merge
from app.news.services.incident_details.casualty_status import (
    CasualtyStatusResult,
    merge_casualty_status,
    status_for_incident_row,
    target_location_count_from_extraction,
)
from app.news.services.incident_details.casualty_text import find_count_mentions, has_vague_quantifier
from app.news.services.incidents.incident_change_log import record_incident_change

OUT_CSV = Path(__file__).resolve().parent / "out" / "casualty_status_backfill_dryrun.csv"
STATUSES = (
    "none_mentioned",
    "explicit_none",
    "exact",
    "count_missing",
    "aggregate_only",
)


def _status_from_message(row: dict[str, Any], message: dict[str, Any]) -> CasualtyStatusResult:
    extraction = message.get("extraction_result") or {}
    target_count = target_location_count_from_extraction(
        extraction.get("village"), extraction.get("village_roles"), extraction.get("sub_events")
    )
    return status_for_incident_row(
        message.get("raw_text") or "", extraction, {},
        target_location_count=target_count,
        row_village_id=row.get("village_id"),
        match_result=message.get("match_result"),
    )


def _combine(current: CasualtyStatusResult, incoming: CasualtyStatusResult) -> CasualtyStatusResult:
    values = merge_casualty_status(
        current.status, current.is_preliminary, current.evidence,
        incoming.status, incoming.is_preliminary, incoming.evidence,
        incoming_is_newest=True,
        current_deaths_status=current.deaths_status,
        incoming_deaths_status=incoming.deaths_status,
        current_injuries_status=current.injuries_status,
        incoming_injuries_status=incoming.injuries_status,
        current_remaining_total=current.remaining_total,
        incoming_remaining_total=incoming.remaining_total,
    )
    return CasualtyStatusResult(
        status=values["casualty_status"],
        deaths_status=values.get("casualty_deaths_status", current.deaths_status),
        injuries_status=values.get("casualty_injuries_status", current.injuries_status),
        is_preliminary=values["casualty_is_preliminary"],
        evidence=values["casualty_status_evidence"],
        remaining_total=values.get("casualty_status_remaining_total") or {},
    )


def _merged_sources(db) -> dict[Any, list[int]]:
    rows = db.execute(
        select(IncidentUpdate.incident_id, IncidentUpdate.new_values)
        .where(IncidentUpdate.action == UpdateAction.pipeline_merge)
        .order_by(IncidentUpdate.created_at, IncidentUpdate.id)
    ).all()
    result: dict[Any, list[int]] = defaultdict(list)
    for incident_id, values in rows:
        raw_id = ((values or {}).get("merged_from") or {}).get("raw_message_id")
        if isinstance(raw_id, int) and raw_id not in result[incident_id]:
            result[incident_id].append(raw_id)
    return result


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
        Incident.created_at,
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
    merges = _merged_sources(db)
    merged_ids = {raw_id for ids in merges.values() for raw_id in ids}
    merged_messages = {
        item["id"]: dict(item)
        for item in db.execute(
            select(
                RawMessage.id, RawMessage.raw_text, RawMessage.extraction_result,
                RawMessage.match_result,
            ).where(RawMessage.id.in_(merged_ids))
        ).mappings()
    } if merged_ids else {}
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
        row["merged_message_ids"] = merges.get(row["incident_id"], [])
        row["missing_merged_message_ids"] = []
        row["suppressed_merged_message_ids"] = []
        for raw_id in row["merged_message_ids"]:
            message = merged_messages.get(raw_id)
            if message is None:
                row["missing_merged_message_ids"].append(raw_id)
                continue
            extraction = message.get("extraction_result") or {}
            target_count = target_location_count_from_extraction(
                extraction.get("village"), extraction.get("village_roles"), extraction.get("sub_events")
            )
            matches = (message.get("match_result") or {}).get("village_matches") or []
            incoming = _status_from_message(row, message)
            decision = guard_casualty_merge(
                incident_village_id=row.get("village_id"),
                target_location_count=target_count,
                casualty_scope=extraction.get("casualty_scope"),
                incoming_status=incoming.status,
                village_matches=matches,
            )
            if decision.suppress:
                row["suppressed_merged_message_ids"].append(raw_id)
                continue
            row["derived"] = _combine(row["derived"], incoming)
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


def _classification(row: dict[str, Any]) -> str:
    if row.get("missing_merged_message_ids"):
        return "merged source missing"
    extraction = row.get("extraction_payload") or {}
    matches = (row.get("match_result") or {}).get("village_matches") or []
    if any(item.get("village_match_status") in {"unmatched", "matched_low_confidence"} for item in matches):
        return "unmatched village"
    text = row.get("raw_text") or ""
    mentions = find_count_mentions(text)
    if row["derived"].status == "count_missing":
        if row["target_location_count"] >= 2:
            return "multi-location summary digest"
        if any(item.rule in {"dual", "singular"} for item in mentions):
            return "dual/singular missed"
        if has_vague_quantifier(text, "deaths") or has_vague_quantifier(text, "injuries"):
            return "vague wording"
        return "other"
    if row["derived"].status == "aggregate_only":
        if extraction.get("casualty_scope") == "bulletin_aggregate" or row["target_location_count"] >= 2:
            if extraction.get("village_roles"):
                return "multi-location summary digest"
            return "bulletin total with no breakdown"
    return "other"


def _write_csv(rows: list[dict[str, Any]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        "incident_id", "raw_message_id", "stored_status", "derived_status",
        "deaths_status", "injuries_status", "is_preliminary", "evidence",
        "deaths", "total_deaths", "injuries", "total_injuries", "disagreement",
        "merged_message_ids", "missing_merged_message_ids", "suppressed_merged_message_ids", "classification",
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
                    "merged_message_ids": ";".join(map(str, row["merged_message_ids"])),
                    "missing_merged_message_ids": ";".join(map(str, row["missing_merged_message_ids"])),
                    "suppressed_merged_message_ids": ";".join(map(str, row["suppressed_merged_message_ids"])),
                    "classification": _classification(row),
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
    classified = [row for row in rows if row["derived"].status in {"aggregate_only", "count_missing"} or _disagreements(row)]
    classes = Counter(_classification(row) for row in classified)
    print(f"classified_remainder: {dict(classes)}")
    print("classified_examples (up to 20):")
    for row in classified[:20]:
        print(f"  {_classification(row)} incident={row['incident_id']} message={row['raw_message_id']} text={(row.get('raw_text') or '')[:240]!r}")
    missing = [(row["incident_id"], raw_id) for row in rows for raw_id in row["missing_merged_message_ids"]]
    print(f"merged_sources_missing: {len(missing)}")
    for incident_id, raw_id in missing[:20]:
        print(f"  incident={incident_id} merged_message={raw_id} skipped=raw_message_missing")
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
