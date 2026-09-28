"""Find and optionally repair aggregate casualty totals leaked through merges.

Dry-run is the default. Never use --apply without reviewing the generated CSV.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.database import SessionLocal
from app.news.models import Incident, IncidentUpdate, RawMessage, UpdateAction
from app.news.services.incident_details.casualty_merge_guard import guard_casualty_merge
from app.news.services.incident_details.casualty_status import target_location_count_from_extraction
from app.news.services.incidents.incident_change_log import record_incident_change

OUT = Path(__file__).resolve().parent / "out" / "casualty_merge_leak_dryrun.csv"
FIELDS = ("deaths", "injuries", "total_deaths", "total_injuries")


def _primary_values(message: dict[str, Any] | None, village_id: int | None) -> dict[str, int | None]:
    if not message:
        return {field: None for field in FIELDS}
    extraction = message.get("extraction_result") or {}
    matches = (message.get("match_result") or {}).get("village_matches") or []
    own = next((item for item in matches if item.get("matched_village_id") == village_id), {})
    target_count = target_location_count_from_extraction(
        extraction.get("village"), extraction.get("village_roles"), extraction.get("sub_events")
    )
    casualties = extraction.get("casualties") or {}
    result: dict[str, int | None] = {}
    for field in FIELDS:
        kind = field.removeprefix("total_")
        value = own.get(field, own.get(kind))
        if value is None and target_count == 1:
            value = casualties.get(field, casualties.get(kind))
        result[field] = value if isinstance(value, int) and not isinstance(value, bool) else None
    return result


def collect(db) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    incidents = {
        row["id"]: dict(row) for row in db.execute(select(
            Incident.id, Incident.raw_message_id, Incident.village_id,
            Incident.deaths, Incident.injuries, Incident.total_deaths,
            Incident.total_injuries, Incident.verification_status,
        ).where(Incident.is_deleted.is_(False))).mappings()
    }
    updates = db.scalars(
        select(IncidentUpdate).where(IncidentUpdate.action == UpdateAction.pipeline_merge)
        .order_by(IncidentUpdate.created_at, IncidentUpdate.id)
    ).all()
    raw_ids = {
        raw_id for update in updates
        if isinstance((raw_id := ((update.new_values or {}).get("merged_from") or {}).get("raw_message_id")), int)
    }
    raw = {
        row["id"]: dict(row) for row in db.execute(
            select(RawMessage.id, RawMessage.raw_text, RawMessage.extraction_result, RawMessage.match_result)
            .where(RawMessage.id.in_(raw_ids))
        ).mappings()
    } if raw_ids else {}
    primary_ids = {item["raw_message_id"] for item in incidents.values() if item["raw_message_id"]}
    primary = {
        row["id"]: dict(row) for row in db.execute(
            select(RawMessage.id, RawMessage.extraction_result, RawMessage.match_result)
            .where(RawMessage.id.in_(primary_ids))
        ).mappings()
    } if primary_ids else {}
    admin_edited = {
        incident_id for incident_id, values in db.execute(
            select(IncidentUpdate.incident_id, IncidentUpdate.new_values)
            .where(IncidentUpdate.performed_by.is_not(None))
        ) if any(field in (values or {}) for field in FIELDS)
    }
    findings: list[dict[str, Any]] = []
    unverifiable: list[dict[str, Any]] = []
    for update in updates:
        incident = incidents.get(update.incident_id)
        if incident is None or incident["verification_status"] == "verified" or incident["id"] in admin_edited:
            continue
        merged_id = ((update.new_values or {}).get("merged_from") or {}).get("raw_message_id")
        if not isinstance(merged_id, int):
            continue
        before, after = update.old_values or {}, update.new_values or {}
        raised = [
            field for field in FIELDS
            if isinstance(after.get(field), int)
            and (before.get(field) is None or (isinstance(before.get(field), int) and after[field] > before[field]))
        ]
        if not raised:
            continue
        message = raw.get(merged_id)
        if message is None:
            unverifiable.append({"incident_id": incident["id"], "merged_message_id": merged_id, "reason": "raw_message_missing"})
            continue
        extraction = message.get("extraction_result") or {}
        target_count = target_location_count_from_extraction(
            extraction.get("village"), extraction.get("village_roles"), extraction.get("sub_events")
        )
        decision = guard_casualty_merge(
            incident_village_id=incident["village_id"],
            target_location_count=target_count,
            casualty_scope=extraction.get("casualty_scope"),
            incoming_status=extraction.get("casualty_status"),
            village_matches=(message.get("match_result") or {}).get("village_matches") or [],
        )
        if not decision.suppress:
            continue
        proposed = _primary_values(primary.get(incident["raw_message_id"]), incident["village_id"])
        for field in raised:
            old, new = before.get(field), after.get(field)
            findings.append({
                "incident_id": incident["id"], "merged_message_id": merged_id, "field": field,
                "old_value": old, "new_value": new, "proposed_value": proposed[field],
                "source_sentence": (message.get("raw_text") or "")[:500],
                "reason": decision.reason,
            })
    return findings, unverifiable


def write_csv(findings: list[dict[str, Any]], unverifiable: list[dict[str, Any]]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ("incident_id", "merged_message_id", "field", "old_value", "new_value", "proposed_value", "source_sentence", "reason")
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        writer.writerows(findings)
        for row in unverifiable:
            writer.writerow({**row, "field": "", "old_value": "", "new_value": "", "proposed_value": "", "source_sentence": ""})


def apply(findings: list[dict[str, Any]], db) -> dict[str, int]:
    result = {"processed": 0, "succeeded": 0, "failed": 0}
    grouped: dict[Any, dict[str, Any]] = {}
    for row in findings:
        grouped.setdefault(row["incident_id"], {})[row["field"]] = row["proposed_value"]
    for incident_id, values in grouped.items():
        result["processed"] += 1
        incident = db.get(Incident, incident_id)
        if incident is None: result["failed"] += 1; continue
        old = {field: getattr(incident, field) for field in values}
        for field, value in values.items(): setattr(incident, field, value)
        record_incident_change(db, incident_id=incident_id, action=UpdateAction.edit,
                               old_values=old, new_values={**values, "casualty_merge_leak_cleanup": True}, performed_by=None)
        result["succeeded"] += 1
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        findings, unverifiable = collect(db); write_csv(findings, unverifiable)
        print(f"leaked_fields: {len(findings)}"); print(f"unverifiable: {len(unverifiable)}")
        for row in findings: print(f"{row['incident_id']} message={row['merged_message_id']} {row['field']} {row['old_value']} -> {row['new_value']} -> {row['proposed_value']}")
        for row in unverifiable[:50]: print(f"{row['incident_id']} message={row['merged_message_id']} unverifiable")
        print(f"csv: {OUT}")
        if args.apply:
            db.rollback()
            with db.begin(): print(f"apply: {apply(findings, db)}")


if __name__ == "__main__": main()
