"""Read-only audit for incidents exposed to cross-region village-name collisions."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.core.database import SessionLocal
from app.core.text_normalization import normalize_arabic_text

ZIBDINE_ACS_CODES = frozenset({26246, 71122})
ALIAS_DATA_PATH = Path("Data/VillageLocationAliases.json")
DEFAULT_OUTPUT = Path("scripts/output/village_name_collision_audit.csv")


def _village_mentions(extraction_result: dict[str, Any]) -> list[str]:
    roles = extraction_result.get("village_roles")
    if isinstance(roles, list) and roles:
        return [
            str(entry["village"]).strip()
            for entry in roles
            if isinstance(entry, dict) and entry.get("village")
        ]
    villages = extraction_result.get("village")
    if isinstance(villages, list):
        return [str(value).strip() for value in villages if str(value).strip()]
    if isinstance(villages, str) and villages.strip():
        return [villages.strip()]
    return []


def _match_entries(match_result: dict[str, Any]) -> list[dict[str, Any]]:
    entries = match_result.get("village_matches")
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, dict)]
    return [match_result] if match_result else []


def _build_risk_groups(
    village_rows: list[dict[str, Any]],
) -> tuple[set[int], dict[int, set[int]]]:
    normalized_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in village_rows:
        normalized = normalize_arabic_text(
            row["ref_name_ar"] or "",
            compact=True,
        )
        if normalized:
            normalized_groups[normalized].append(row)

    groups: list[list[dict[str, Any]]] = []
    for rows in normalized_groups.values():
        regions = {(row["caza_en"], row["mohafaza_en"]) for row in rows}
        if len(rows) > 1 and len(regions) > 1:
            groups.append(rows)

    zibdine_rows = [
        row for row in village_rows if row["acs_code"] in ZIBDINE_ACS_CODES
    ]
    if len(zibdine_rows) != len(ZIBDINE_ACS_CODES):
        missing = ZIBDINE_ACS_CODES - {
            row["acs_code"] for row in zibdine_rows
        }
        raise RuntimeError(f"Missing expected Zebdine ACS rows: {sorted(missing)}")
    groups.append(zibdine_rows)

    alternates: dict[int, set[int]] = defaultdict(set)
    for rows in groups:
        ids = {int(row["id"]) for row in rows}
        for village_id in ids:
            alternates[village_id].update(ids - {village_id})
    return set(alternates), alternates


def _known_mentions_by_village_id(
    village_rows: list[dict[str, Any]],
) -> dict[int, set[str]]:
    by_id: dict[int, set[str]] = defaultdict(set)
    id_by_acs = {int(row["acs_code"]): int(row["id"]) for row in village_rows}
    for row in village_rows:
        if row["ref_name_ar"]:
            by_id[int(row["id"])].add(str(row["ref_name_ar"]))

    alias_rows = json.loads(ALIAS_DATA_PATH.read_text(encoding="utf-8"))
    for alias in alias_rows:
        village_id = id_by_acs.get(int(alias["parent_acs_code"]))
        if village_id is not None:
            by_id[village_id].add(str(alias["alias_text"]))
    return by_id


def _raw_only_villages(
    raw_text: str,
    extracted_mentions: list[str],
    known_mentions: dict[int, set[str]],
) -> list[int]:
    normalized_raw = normalize_arabic_text(raw_text)
    extracted = {
        normalize_arabic_text(mention) for mention in extracted_mentions
    }
    detected: list[int] = []
    for village_id, mentions in known_mentions.items():
        for mention in mentions:
            normalized = normalize_arabic_text(mention)
            if (
                len(normalized) >= 4
                and re.search(
                    rf"(?<![\u0600-\u06ff]){re.escape(normalized)}"
                    rf"(?![\u0600-\u06ff])",
                    normalized_raw,
                )
                and all(
                    normalized not in extracted_name
                    and extracted_name not in normalized
                    for extracted_name in extracted
                )
            ):
                detected.append(village_id)
                break
    return detected


def run_audit(output_path: Path) -> dict[str, int]:
    summary = {
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "villages_checked": 0,
        "incidents_flagged": 0,
        "errors": 0,
    }
    db = SessionLocal()
    try:
        db.execute(text("SET TRANSACTION READ ONLY"))
        village_rows = [
            dict(row)
            for row in db.execute(
                text(
                    """
                    SELECT id, acs_code, acs_name, ref_name_en, ref_name_ar,
                           caza_en, mohafaza_en
                    FROM villages
                    WHERE is_active = true
                    """
                )
            ).mappings()
        ]
        at_risk_ids, alternates = _build_risk_groups(village_rows)
        summary["villages_checked"] = len(at_risk_ids)
        villages_by_id = {int(row["id"]): row for row in village_rows}
        known_mentions = _known_mentions_by_village_id(village_rows)

        rows = db.execute(
            text(
                """
                SELECT
                    i.id AS incident_id,
                    i.raw_message_id AS canonical_raw_message_id,
                    i.village_id,
                    r.id AS raw_message_id,
                    r.raw_text,
                    r.extraction_result,
                    r.match_result,
                    EXISTS (
                        SELECT 1
                        FROM incident_updates AS updates
                        WHERE updates.incident_id = i.id
                          AND (
                            updates.old_values ? 'village_id'
                            OR updates.new_values ? 'village_id'
                            OR updates.old_values ? 'village'
                            OR updates.new_values ? 'village'
                          )
                    ) AS admin_corrected
                FROM incidents AS i
                JOIN raw_messages AS r
                  ON r.id = i.raw_message_id
                  OR r.duplicate_of_id = i.raw_message_id
                WHERE i.is_deleted = false
                  AND i.village_id = ANY(:at_risk_ids)
                ORDER BY i.created_at, r.id
                """
            ),
            {"at_risk_ids": sorted(at_risk_ids)},
        ).mappings()

        report_rows: list[dict[str, Any]] = []
        flagged_incident_ids: set[str] = set()
        for row in rows:
            summary["processed"] += 1
            try:
                extraction = (
                    row["extraction_result"]
                    if isinstance(row["extraction_result"], dict)
                    else {}
                )
                match_result = (
                    row["match_result"]
                    if isinstance(row["match_result"], dict)
                    else {}
                )
                extracted_mentions = _village_mentions(extraction)
                entries = _match_entries(match_result)
                matched_mentions = [
                    str(entry.get("raw_village_text") or "").strip()
                    for entry in entries
                    if entry.get("raw_village_text")
                ]
                matched_norms = {
                    normalize_arabic_text(value) for value in matched_mentions
                }
                dropped = [
                    mention
                    for mention in extracted_mentions
                    if normalize_arabic_text(mention) not in matched_norms
                ]
                selected_entry = next(
                    (
                        entry
                        for entry in entries
                        if entry.get("matched_village_id") == row["village_id"]
                    ),
                    {},
                )
                low_confidence = (
                    selected_entry.get("village_match_status")
                    == "matched_low_confidence"
                    and not row["admin_corrected"]
                )
                raw_only_ids = _raw_only_villages(
                    row["raw_text"] or "",
                    extracted_mentions,
                    known_mentions,
                )
                raw_only_ids = [
                    village_id
                    for village_id in raw_only_ids
                    if village_id != row["village_id"]
                ]
                reasons = []
                if dropped:
                    reasons.append("extracted_location_missing_from_match")
                if raw_only_ids:
                    reasons.append("known_raw_location_missing_from_extraction")
                if low_confidence:
                    reasons.append("uncorrected_low_confidence_match")
                if not reasons:
                    summary["succeeded"] += 1
                    continue

                alternate_ids = set(alternates[int(row["village_id"])])
                alternate_ids.update(raw_only_ids)
                alternate_names = sorted(
                    str(
                        villages_by_id[village_id]["ref_name_en"]
                        or villages_by_id[village_id]["acs_name"]
                        or villages_by_id[village_id]["ref_name_ar"]
                    )
                    for village_id in alternate_ids
                    if village_id in villages_by_id
                )
                matched_village = villages_by_id[int(row["village_id"])]
                report_rows.append(
                    {
                        "incident_id": row["incident_id"],
                        "canonical_raw_message_id": row[
                            "canonical_raw_message_id"
                        ],
                        "raw_message_id": row["raw_message_id"],
                        "matched_village_id": row["village_id"],
                        "matched_village": (
                            matched_village["ref_name_en"]
                            or matched_village["acs_name"]
                            or matched_village["ref_name_ar"]
                        ),
                        "reasons": ";".join(reasons),
                        "extracted_mentions": " | ".join(extracted_mentions),
                        "matched_mentions": " | ".join(matched_mentions),
                        "dropped_extracted_mentions": " | ".join(dropped),
                        "alternate_candidates": " | ".join(alternate_names),
                        "raw_text": row["raw_text"] or "",
                    }
                )
                flagged_incident_ids.add(str(row["incident_id"]))
                summary["succeeded"] += 1
            except Exception:
                summary["failed"] += 1
                summary["errors"] += 1

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "incident_id",
            "canonical_raw_message_id",
            "raw_message_id",
            "matched_village_id",
            "matched_village",
            "reasons",
            "extracted_mentions",
            "matched_mentions",
            "dropped_extracted_mentions",
            "alternate_candidates",
            "raw_text",
        ]
        with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(report_rows)
        summary["incidents_flagged"] = len(flagged_incident_ids)
        db.rollback()
        return summary
    except Exception:
        db.rollback()
        summary["failed"] += 1
        summary["errors"] += 1
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    started_at = datetime.now(timezone.utc)
    summary = run_audit(args.output)
    print(
        json.dumps(
            {
                **summary,
                "output": str(args.output),
                "started_at": started_at.isoformat(),
            },
            sort_keys=True,
        )
    )
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
