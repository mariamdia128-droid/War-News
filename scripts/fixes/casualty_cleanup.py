"""Clean casualty values that the casualty-foundations backstop shows are wrong.

DRY-RUN BY DEFAULT. Nothing is written unless ``--apply`` is passed.

Cases (all detected by rule, not by id):
  A  leaked bulletin total: a multi-location message whose root aggregate sits
     on 2+ of its village rows with no per-village evidence for that value.
  B  stored 0 without an explicit-none phrase («دون تسجيل إصابات») in the source.
  C  a single value the tightened count backstop rejects for the row's own
     message (vague phrase, strike-count list, date/URL digit, no evidence).
  R  review only, never changed: a bulletin total on the only remaining row of
     a multi-location message, or a C value that a merged message also states.

Rows that are ``verified`` or were edited by an admin are skipped. Rows are
never deleted and verification fields are never touched.

Usage (inside the backend container):
    python -m scripts.fixes.casualty_cleanup            # dry run + CSV
    python -m scripts.fixes.casualty_cleanup --apply    # one transaction
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.text_normalization import normalize_arabic_text
from app.llm.dtos import CasualtyCountEvidence, ExtractionCasualties, ExtractionResult
from app.news.models.incident_update import UpdateAction
from app.news.services.incident_details.casualty_count_backstop import (
    apply_casualty_count_backstop,
)
from app.news.services.incident_details.casualty_text import (
    DEATHS,
    INJURIES,
    find_supporting_mention,
    has_explicit_none,
    sentences,
)
from app.news.services.incidents.incident_change_log import record_incident_change

OUT_DIR = Path(__file__).resolve().parent / "out"
DRY_RUN_CSV = OUT_DIR / "casualty_cleanup_dryrun.csv"
CLEANUP_TAG = "casualty_cleanup"
FIELDS_BY_KIND = {
    DEATHS: ("deaths", "total_deaths"),
    INJURIES: ("injuries", "total_injuries"),
}
COUNT_FIELDS = ("deaths", "injuries", "total_deaths", "total_injuries")


@dataclass
class Change:
    incident_id: str
    raw_message_id: int
    case: str
    field: str
    old_value: int
    new_value: int | None
    action: str  # update | review
    reason: str


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _extraction(payload: Any) -> ExtractionResult | None:
    if not isinstance(payload, dict):
        return None
    try:
        return ExtractionResult.model_validate(payload)
    except ValidationError:
        return None


def _target_matches(match_result: Any) -> list[dict[str, Any]]:
    if not isinstance(match_result, dict):
        return []
    return [
        item
        for item in match_result.get("village_matches") or []
        if isinstance(item, dict) and item.get("village_role", "target") == "target"
    ]


def _match_for_village(match_result: Any, village_id: int | None) -> dict[str, Any] | None:
    for item in _target_matches(match_result):
        if _int(item.get("matched_village_id")) == village_id:
            return item
    return None


def _per_village_value(
    extraction: ExtractionResult | None,
    match: dict[str, Any] | None,
    kind: str,
) -> int | None:
    """Count the message itself attributes to this village (match entry / sub-event)."""
    if match is None:
        return None
    value = _int(match.get(kind))
    if value is not None:
        return value
    event_index = _int(match.get("event_index"))
    if extraction is not None and event_index is not None and 0 <= event_index < len(
        extraction.sub_events
    ):
        sub_event = extraction.sub_events[event_index]
        if len({loc.village for loc in sub_event.locations}) <= 1:
            return getattr(sub_event.casualties, kind)
    return None


def _sentence_owner(
    raw_text: str, kind: str, value: int, target_texts: list[str]
) -> set[str]:
    """Targets named alone in a sentence that states *value* for *kind*.

    «ارتكب العدو مجازر في بلدة كفررمان حيث ارتقى 9 شهداء» ties 9 to كفررمان.
    """
    keys = {name: normalize_arabic_text(name, compact=True) for name in target_texts if name}
    owners: set[str] = set()
    for sentence in sentences(raw_text):
        if find_supporting_mention(sentence, kind, value) is None:
            continue
        compact = normalize_arabic_text(sentence, compact=True)
        named = {name for name, key in keys.items() if key and key in compact}
        if len(named) == 1:
            owners |= named
    return owners


def _root_aggregates(extraction: ExtractionResult | None, kind: str) -> set[int]:
    if extraction is None:
        return set()
    casualties = extraction.casualties
    return {
        value
        for value in (getattr(casualties, kind), getattr(casualties, f"total_{kind}"))
        if value
    }


def _rejected_by_backstop(
    raw_text: str,
    extraction: ExtractionResult | None,
    match: dict[str, Any] | None,
) -> dict[str, tuple[int, str]]:
    """{kind: (original value, source)} for counts the new backstop nulls."""
    if extraction is None:
        return {}
    rejected: dict[str, tuple[int, str]] = {}
    role = None
    if match is not None:
        raw_village = match.get("raw_village_text")
        role = next(
            (entry for entry in extraction.village_roles if entry.village == raw_village),
            None,
        )
    if role is not None and (role.deaths is not None or role.injuries is not None):
        evidence = [
            CasualtyCountEvidence(field=kind, evidence_span=role.evidence_span)
            for kind in (DEATHS, INJURIES)
            if role.evidence_span and getattr(role, kind) is not None
        ]
        original = ExtractionCasualties(deaths=role.deaths, injuries=role.injuries)
        checked, _ = apply_casualty_count_backstop(raw_text, original, evidence)
        for kind in (DEATHS, INJURIES):
            value = getattr(original, kind)
            if value and getattr(checked, kind) is None:
                rejected[kind] = (value, "village_role")
    checked, _ = apply_casualty_count_backstop(
        raw_text, extraction.casualties, list(extraction.casualty_evidence)
    )
    for kind in (DEATHS, INJURIES):
        if kind in rejected:
            continue
        for field in (kind, f"total_{kind}"):
            value = getattr(extraction.casualties, field)
            if value and getattr(checked, field) is None:
                rejected[kind] = (value, "root")
                break
    return rejected


def _load(db) -> tuple[list[dict[str, Any]], dict[int, list[dict[str, Any]]], set[str], dict]:
    rows = [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT i.id::text AS id, i.raw_message_id, i.village_id,
                       i.deaths, i.injuries, i.total_deaths, i.total_injuries,
                       i.verification_status,
                       rm.raw_text, rm.extraction_result, rm.match_result
                FROM incidents i
                JOIN raw_messages rm ON rm.id = i.raw_message_id
                WHERE NOT i.is_deleted
                ORDER BY i.raw_message_id, i.id
                """
            )
        ).mappings()
    ]
    by_message: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_message[row["raw_message_id"]].append(row)
    admin_edited = {
        row[0]
        for row in db.execute(
            text(
                "SELECT DISTINCT incident_id::text FROM incident_updates "
                "WHERE action = 'edit' AND performed_by IS NOT NULL"
            )
        )
    }
    merges: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for incident_id, new_values in db.execute(
        text(
            "SELECT incident_id::text, new_values FROM incident_updates "
            "WHERE action = 'pipeline_merge'"
        )
    ):
        if isinstance(new_values, dict):
            merges[incident_id].append(new_values)
    return rows, by_message, admin_edited, merges


def _supported_by_other_message(
    merges: list[dict[str, Any]], raw_message_id: int, field: str, value: int
) -> bool:
    """True when a message merged into this row states *value* for *field*."""
    for new_values in merges:
        merged_from = new_values.get("merged_from") or {}
        source = merged_from.get("raw_message_id")
        if source is None or source == raw_message_id or new_values.get(field) != value:
            continue
        if find_supporting_mention(merged_from.get("khabar") or "", field, value):
            return True
    return False


def plan_changes(db) -> tuple[list[Change], int]:
    rows, by_message, admin_edited, merges = _load(db)
    changes: list[Change] = []
    skipped_protected = 0

    for raw_message_id, message_rows in by_message.items():
        sample = message_rows[0]
        extraction = _extraction(sample["extraction_result"])
        raw_text = sample["raw_text"] or ""
        live_villages = {row["village_id"] for row in message_rows}
        message_targets = {
            _int(item.get("matched_village_id"))
            for item in _target_matches(sample["match_result"])
        } - {None}
        target_names = {role.village for role in (extraction.village_roles if extraction else [])}
        target_texts = [
            item.get("raw_village_text") for item in _target_matches(sample["match_result"])
        ]
        is_multi_location = len(live_villages) > 1
        claims_multi = len(message_targets | live_villages) > 1 or len(target_names) > 1

        for row in message_rows:
            values = {field: _int(row[field]) for field in COUNT_FIELDS}
            if all(value is None for value in values.values()):
                continue
            if row["verification_status"] == "verified" or row["id"] in admin_edited:
                skipped_protected += 1
                continue
            match = _match_for_village(sample["match_result"], row["village_id"])
            handled: set[str] = set()

            # Case B: zero without an explicit-none phrase.
            for kind, fields in FIELDS_BY_KIND.items():
                for field in fields:
                    if values[field] == 0 and not has_explicit_none(raw_text, kind):
                        changes.append(
                            Change(row["id"], raw_message_id, "B", field, 0, None, "update",
                                   "zero_without_explicit_none")
                        )
                        handled.add(field)

            for kind, fields in FIELDS_BY_KIND.items():
                aggregates = _root_aggregates(extraction, kind)
                own_value = _per_village_value(extraction, match, kind)
                for aggregate in aggregates:
                    if not any(values[field] == aggregate for field in fields):
                        continue
                    if own_value == aggregate:
                        continue  # per-village evidence for this value
                    row_name = (match or {}).get("raw_village_text")
                    if row_name and row_name in _sentence_owner(
                        raw_text, kind, aggregate, target_texts
                    ):
                        continue  # the text ties this value to this village alone
                    same_rows = sum(
                        1
                        for other in message_rows
                        if any(_int(other[field]) == aggregate for field in fields)
                    )
                    if is_multi_location and same_rows >= 2:
                        # Case A: bulletin total copied onto several village rows.
                        for field in fields:
                            if values[field] == aggregate and field not in handled:
                                changes.append(
                                    Change(row["id"], raw_message_id, "A", field, aggregate,
                                           None, "update",
                                           f"bulletin_total_on_{same_rows}_village_rows")
                                )
                                handled.add(field)
                    elif not is_multi_location and claims_multi and own_value is None:
                        # Case R: bulletin total on the only remaining row.
                        for field in fields:
                            if values[field] == aggregate and field not in handled:
                                changes.append(
                                    Change(row["id"], raw_message_id, "R", field, aggregate,
                                           aggregate, "review",
                                           "bulletin_total_on_single_remaining_row")
                                )
                                handled.add(field)

            # Case C: a value from this message that the tightened backstop rejects.
            for kind, (value, source) in _rejected_by_backstop(raw_text, extraction, match).items():
                for field in FIELDS_BY_KIND[kind]:
                    if field in handled or values[field] != value:
                        continue
                    if _supported_by_other_message(merges[row["id"]], raw_message_id, field, value):
                        changes.append(
                            Change(row["id"], raw_message_id, "R", field, value, value, "review",
                                   f"backstop_rejects_{source}_value_but_a_merged_message_states_it")
                        )
                    else:
                        changes.append(
                            Change(row["id"], raw_message_id, "C", field, value, None, "update",
                                   f"backstop_rejects_{source}_value")
                        )
                    handled.add(field)

    return changes, skipped_protected


def _write_csv(path: Path, changes: list[Change]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(Change.__dataclass_fields__))
        writer.writeheader()
        for change in changes:
            writer.writerow(asdict(change))


def _print_table(changes: list[Change]) -> None:
    print(f"{'incident_id':36}  {'message':>7}  case  {'field':14}  old  new   action  reason")
    for change in changes:
        new = "NULL" if change.new_value is None else str(change.new_value)
        print(
            f"{change.incident_id:36}  {change.raw_message_id:>7}  {change.case:4}  "
            f"{change.field:14}  {change.old_value:>3}  {new:>4}  {change.action:6}  {change.reason}"
        )


def apply_changes(db, changes: list[Change]) -> tuple[int, int, int]:
    """Apply update rows in the caller's transaction; returns processed/succeeded/failed."""
    by_incident: dict[str, list[Change]] = defaultdict(list)
    for change in changes:
        if change.action == "update":
            by_incident[change.incident_id].append(change)
    processed = succeeded = failed = 0
    for incident_id, items in by_incident.items():
        processed += 1
        assignments = ", ".join(f"{item.field} = NULL" for item in items)
        guards = " AND ".join(f"{item.field} = :old_{item.field}" for item in items)
        result = db.execute(
            text(
                f"UPDATE incidents SET {assignments}, version = version + 1, "
                f"updated_at = now() WHERE id = CAST(:id AS uuid) AND {guards}"
            ),
            {"id": incident_id, **{f"old_{item.field}": item.old_value for item in items}},
        )
        if result.rowcount != 1:
            failed += 1
            print(f"stale, not updated: {incident_id}")
            continue
        record_incident_change(
            db,
            incident_id=incident_id,
            action=UpdateAction.edit,
            old_values={item.field: item.old_value for item in items},
            new_values={
                **{item.field: None for item in items},
                "source": CLEANUP_TAG,
                "reasons": {item.field: f"{item.case}:{item.reason}" for item in items},
            },
            performed_by=None,
        )
        succeeded += 1
    return processed, succeeded, failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--apply", action="store_true", help="write the update rows")
    args = parser.parse_args()

    with SessionLocal() as db:
        changes, skipped_protected = plan_changes(db)
        _print_table(changes)
        _write_csv(DRY_RUN_CSV, changes)
        updates = [change for change in changes if change.action == "update"]
        by_case: dict[str, int] = defaultdict(int)
        for change in changes:
            by_case[change.case] += 1
        print(
            f"\nplanned field changes={len(updates)} "
            f"incidents={len({change.incident_id for change in updates})} "
            f"review_only={len(changes) - len(updates)} by_case={dict(sorted(by_case.items()))} "
            f"skipped_verified_or_admin_edited={skipped_protected}"
        )
        print(f"csv: {DRY_RUN_CSV}")

        if not args.apply:
            db.rollback()
            print("Dry run only. Re-run with --apply to write updates.")
            return

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        applied_csv = OUT_DIR / f"casualty_cleanup_apply_{stamp}.csv"
        _write_csv(applied_csv, updates)  # old values on disk before any write
        try:
            processed, succeeded, failed = apply_changes(db, changes)
            db.commit()
        except Exception:
            db.rollback()
            print("Failed; rolled back. No rows changed.")
            raise
        print(f"processed={processed} succeeded={succeeded} failed={failed} csv={applied_csv}")


if __name__ == "__main__":
    main()
