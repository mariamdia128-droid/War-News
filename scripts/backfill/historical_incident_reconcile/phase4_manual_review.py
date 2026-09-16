#!/usr/bin/env python
"""Phase 4: generate manual-review-only historical reconciliation reports."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.llm.dtos import ExtractionResult
from app.news.repositories.condition_repository import ConditionRepository
from app.news.repositories.village_repository import VillageRepository
from app.news.services.matching.matching_service import MatchingService
from scripts.backfill.historical_incident_reconcile.common import (
    DEFAULT_OUTPUT_DIR,
    open_read_only_session,
    utc_now,
    write_json,
)
from scripts.backfill.historical_incident_reconcile.phase1_reextract import (
    RECON_CUTOFF,
)
from scripts.backfill.historical_incident_reconcile.phase2_village import (
    _entry_key,
    _population_a_ids,
)

PHASE = "phase4_manual_review"


def _old_candidates(row: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    entries = (row.get("match_result") or {}).get("village_matches") or []
    return [
        (index, entry)
        for index, entry in enumerate(entries)
        if isinstance(entry, dict)
        and entry.get("village_role", "target") == "target"
        and entry.get("matched_village_id") == row["village_id"]
        and entry.get("village_match_status")
        in {"matched", "matched_low_confidence"}
    ]


def discover_village_manual_items(db: Any) -> dict[str, list[dict[str, Any]]]:
    rows = [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT i.id::text AS incident_id, i.raw_message_id,
                       i.village_id, i.condition_id, i.is_deleted,
                       r.raw_text, r.extraction_result, r.match_result
                FROM incidents i
                JOIN raw_messages r ON r.id = i.raw_message_id
                ORDER BY i.id
                """
            )
        ).mappings()
    ]
    matcher = MatchingService(VillageRepository(db), ConditionRepository(db))
    rematched: dict[int, list[dict[str, Any]]] = {}
    ambiguous_attribution: list[dict[str, Any]] = []
    ambiguous_binding: list[dict[str, Any]] = []
    unbindable: list[dict[str, Any]] = []
    for row in rows:
        candidates = _old_candidates(row)
        if not candidates:
            unbindable.append(
                {
                    "incident_id": row["incident_id"],
                    "raw_message_id": row["raw_message_id"],
                    "current_village_id": row["village_id"],
                    "condition_id": row["condition_id"],
                    "is_deleted": row["is_deleted"],
                    "reason": "no_old_target_match_for_current_incident_village",
                    "raw_text": row["raw_text"],
                }
            )
            continue

        raw_id = int(row["raw_message_id"])
        if raw_id not in rematched:
            rematched[raw_id] = matcher.match(
                ExtractionResult.model_validate(row["extraction_result"])
            ).model_dump(mode="json")["village_matches"]
        new_entries = rematched[raw_id]
        mapped = [
            new_entries[index]
            for index, _entry in candidates
            if index < len(new_entries)
        ]
        mapped_ids = {
            entry.get("matched_village_id")
            for entry in mapped
            if isinstance(entry.get("matched_village_id"), int)
        }
        changed = any(
            village_id != row["village_id"] for village_id in mapped_ids
        )
        if len(candidates) > 1 and changed:
            item = {
                "incident_id": row["incident_id"],
                "raw_message_id": raw_id,
                "current_village_id": row["village_id"],
                "is_deleted": row["is_deleted"],
                "reason": "multiple_old_target_entries_with_changed_resolution",
                "old_candidates": [entry for _, entry in candidates],
                "corresponding_new_entries": mapped,
                "raw_text": row["raw_text"],
            }
            ambiguous_attribution.append(item)
            if len(mapped_ids) > 1:
                ambiguous_binding.append(
                    {
                        **item,
                        "reason": (
                            "one_incident_maps_to_multiple_distinct_fixed_villages"
                        ),
                        "overlaps_ambiguous_village_attribution": True,
                    }
                )
            continue

        if len(candidates) == 1:
            old_index, old_entry = candidates[0]
            same_key = [
                entry
                for entry in new_entries
                if _entry_key(entry) == _entry_key(old_entry)
            ]
            if len(same_key) != 1:
                ambiguous_binding.append(
                    {
                        "incident_id": row["incident_id"],
                        "raw_message_id": raw_id,
                        "current_village_id": row["village_id"],
                        "is_deleted": row["is_deleted"],
                        "reason": "fixed_match_entry_identity_not_unique",
                        "old_entry": old_entry,
                        "same_key_candidates": same_key,
                        "ordinal_fallback_entry": (
                            new_entries[old_index]
                            if old_index < len(new_entries)
                            else None
                        ),
                        "raw_text": row["raw_text"],
                    }
                )
    return {
        "ambiguous_village_attribution": ambiguous_attribution,
        "additional_ambiguous_binding": ambiguous_binding,
        "not_bindable_to_old_target": unbindable,
    }


def discover_no_direct_incidents(db: Any) -> list[dict[str, Any]]:
    population_a = _population_a_ids(db)
    return [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT r.id AS raw_message_id, r.status::text AS status,
                       r.duplicate_of_id, r.raw_text, r.received_at,
                  COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                      'duplicate_match_id', dm.id,
                      'status', dm.status::text,
                      'incident_id', dm.incident_id,
                      'matched_incident_id', dm.matched_incident_id,
                      'incident_live', NOT i.is_deleted
                    ) ORDER BY dm.id)
                    FROM duplicate_matches dm
                    JOIN incidents i ON i.id = dm.incident_id
                    WHERE dm.raw_message_id = r.id
                  ), '[]'::jsonb) AS duplicate_links,
                  COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                      'update_id', iu.id,
                      'incident_id', iu.incident_id,
                      'incident_live', NOT i.is_deleted,
                      'story_revision', iu.new_values->'story_revision'
                    ) ORDER BY iu.id)
                    FROM incident_updates iu
                    JOIN incidents i ON i.id = iu.incident_id
                    WHERE iu.new_values->'merged_from'->>'raw_message_id'
                      = r.id::text
                  ), '[]'::jsonb) AS merged_update_links,
                  COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                      'raw_message_id', child.id,
                      'status', child.status::text
                    ) ORDER BY child.id)
                    FROM raw_messages child
                    WHERE child.duplicate_of_id = r.id
                  ), '[]'::jsonb) AS later_duplicate_messages
                FROM raw_messages r
                WHERE r.id = ANY(:population_a)
                  AND NOT EXISTS (
                    SELECT 1 FROM incidents i WHERE i.raw_message_id = r.id
                  )
                ORDER BY r.id
                """
            ),
            {"population_a": sorted(population_a) or [0]},
        ).mappings()
    ]


def classify_no_direct(item: dict[str, Any]) -> str:
    has_duplicate = bool(item.get("duplicate_links"))
    has_update = bool(item.get("merged_update_links"))
    if has_duplicate and has_update:
        return "duplicate_and_merge_update_only"
    if has_duplicate:
        return "confirmed_or_pending_duplicate_only"
    if has_update:
        return "merge_or_story_revision_only"
    if item.get("duplicate_of_id") is not None:
        return "raw_duplicate_pointer_only"
    return "no_incident_or_provenance_link_found"


def markdown_report(payload: dict[str, Any]) -> str:
    counts = payload["summary"]
    lines = [
        "# Historical reconciliation manual review",
        "",
        f"Generated: {payload['generated_at']}",
        f"Recon cutoff: {payload['recon_cutoff']}",
        "",
        "No database writes were performed. Nothing in this report is an "
        "automated apply decision.",
        "",
        "## Summary",
        "",
    ]
    for key, value in counts.items():
        lines.append(f"- {key}: {value}")
    for section in (
        "ambiguous_village_attribution",
        "additional_ambiguous_binding",
        "not_bindable_to_old_target",
        "no_direct_incident_messages",
    ):
        lines.extend(["", f"## {section}", ""])
        for item in payload[section]:
            identity = item.get("incident_id") or item.get("raw_message_id")
            reason = item.get("reason") or item.get("classification")
            lines.append(f"- `{identity}` — {reason}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    db = open_read_only_session()
    try:
        village = discover_village_manual_items(db)
        no_direct = discover_no_direct_incidents(db)
        for item in no_direct:
            item["classification"] = classify_no_direct(item)
        classes = Counter(item["classification"] for item in no_direct)
        payload = {
            "phase": PHASE,
            "mode": "manual_review_only",
            "generated_at": utc_now(),
            "recon_cutoff": RECON_CUTOFF,
            "summary": {
                "ambiguous_village_attribution": len(
                    village["ambiguous_village_attribution"]
                ),
                "additional_ambiguous_binding": len(
                    village["additional_ambiguous_binding"]
                ),
                "not_bindable_to_old_target": len(
                    village["not_bindable_to_old_target"]
                ),
                "no_direct_incident_messages": len(no_direct),
                **{f"no_direct_{key}": value for key, value in classes.items()},
            },
            **village,
            "no_direct_incident_messages": no_direct,
        }
        write_json(args.output_dir / f"{PHASE}.json", payload)
        markdown_path = args.output_dir / f"{PHASE}.md"
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(
            markdown_report(payload),
            encoding="utf-8",
        )
        print(
            f"{PHASE} completed: processed="
            f"{sum(payload['summary'][key] for key in ('ambiguous_village_attribution', 'additional_ambiguous_binding', 'not_bindable_to_old_target', 'no_direct_incident_messages'))} "
            "succeeded="
            f"{sum(payload['summary'][key] for key in ('ambiguous_village_attribution', 'additional_ambiguous_binding', 'not_bindable_to_old_target', 'no_direct_incident_messages'))} "
            "failed=0"
        )
        return 0
    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
