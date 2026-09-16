#!/usr/bin/env python
"""Phase 2 dry run: plan village-only corrections outside Population A."""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

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
    JsonlCheckpoint,
    open_read_only_session,
    run_batch,
    tagged_audit_values,
    write_dry_run_report,
    write_json,
)
from scripts.backfill.historical_incident_reconcile.phase1_reextract import (
    RECON_CUTOFF,
)

PHASE = "phase2_village"


@dataclass(frozen=True)
class VillageCorrection:
    incident_id: str
    raw_message_id: int
    is_deleted: bool
    old_village_id: int
    new_village_id: int
    raw_village_text: str | None
    qualifier_text: str | None
    old_status: str | None
    new_status: str | None
    old_confidence: float | None
    new_confidence: float | None


def _entry_key(entry: dict[str, Any]) -> tuple[Any, ...]:
    return (
        entry.get("event_index"),
        entry.get("raw_village_text"),
        entry.get("village_role", "target"),
        entry.get("qualifier_text"),
    )


def _population_a_ids(db: Any) -> set[int]:
    return {
        int(row[0])
        for row in db.execute(
            text(
                """
                SELECT r.id
                FROM raw_messages r
                CROSS JOIN LATERAL jsonb_array_elements(
                  COALESCE(r.match_result->'village_matches', '[]'::jsonb)
                ) village(value)
                WHERE r.status::text IN ('parsed', 'materialized')
                  AND COALESCE(r.materialized_at, r.matched_at, r.received_at)
                    <= CAST(:recon_cutoff AS timestamptz)
                GROUP BY r.id
                HAVING count(
                  DISTINCT (village.value->>'matched_village_id')::int
                ) FILTER (
                  WHERE village.value->>'village_match_status'
                    IN ('matched', 'matched_low_confidence')
                    AND (village.value->>'matched_village_id') ~ '^[0-9]+$'
                ) > 1
                """
            ),
            {"recon_cutoff": RECON_CUTOFF},
        )
    }


def discover_corrections() -> tuple[
    list[VillageCorrection],
    list[dict[str, Any]],
]:
    db = open_read_only_session()
    try:
        population_a = _population_a_ids(db)
        rows = list(
            db.execute(
                text(
                    """
                    SELECT i.id::text AS incident_id, i.raw_message_id,
                           i.village_id, i.is_deleted,
                           r.extraction_result, r.match_result
                    FROM incidents i
                    JOIN raw_messages r ON r.id = i.raw_message_id
                    WHERE i.village_id IS NOT NULL
                      AND NOT (i.raw_message_id = ANY(:population_a))
                    ORDER BY i.id
                    """
                ),
                {"population_a": sorted(population_a) or [0]},
            ).mappings()
        )
        matcher = MatchingService(
            VillageRepository(db),
            ConditionRepository(db),
        )
        rematched: dict[int, list[dict[str, Any]]] = {}
        corrections: list[VillageCorrection] = []
        manual: list[dict[str, Any]] = []
        for row in rows:
            old_result = dict(row["match_result"] or {})
            old_entries = [
                entry
                for entry in old_result.get("village_matches") or []
                if isinstance(entry, dict)
            ]
            candidates = [
                (index, entry)
                for index, entry in enumerate(old_entries)
                if entry.get("village_role", "target") == "target"
                and entry.get("matched_village_id") == row["village_id"]
                and entry.get("village_match_status")
                in {"matched", "matched_low_confidence"}
            ]
            if len(candidates) != 1:
                manual.append(
                    {
                        "incident_id": row["incident_id"],
                        "raw_message_id": row["raw_message_id"],
                        "reason": (
                            "old_target_match_not_bindable"
                            if not candidates
                            else "multiple_old_target_matches"
                        ),
                        "candidate_count": len(candidates),
                        "current_village_id": row["village_id"],
                    }
                )
                continue

            raw_id = int(row["raw_message_id"])
            if raw_id not in rematched:
                extraction = ExtractionResult.model_validate(
                    row["extraction_result"]
                )
                rematched[raw_id] = matcher.match(extraction).model_dump(
                    mode="json"
                )["village_matches"]
            new_entries = rematched[raw_id]
            old_index, old_entry = candidates[0]
            same_key = [
                entry
                for entry in new_entries
                if _entry_key(entry) == _entry_key(old_entry)
            ]
            if len(same_key) == 1:
                new_entry = same_key[0]
            elif old_index < len(new_entries):
                new_entry = new_entries[old_index]
            else:
                manual.append(
                    {
                        "incident_id": row["incident_id"],
                        "raw_message_id": raw_id,
                        "reason": "new_match_entry_not_bindable",
                        "candidate_count": len(same_key),
                        "current_village_id": row["village_id"],
                    }
                )
                continue
            new_id = new_entry.get("matched_village_id")
            if not isinstance(new_id, int) or isinstance(new_id, bool):
                manual.append(
                    {
                        "incident_id": row["incident_id"],
                        "raw_message_id": raw_id,
                        "reason": "new_match_unresolved",
                        "current_village_id": row["village_id"],
                        "new_entry": new_entry,
                    }
                )
                continue
            if new_id == row["village_id"]:
                continue
            corrections.append(
                VillageCorrection(
                    incident_id=row["incident_id"],
                    raw_message_id=raw_id,
                    is_deleted=bool(row["is_deleted"]),
                    old_village_id=int(row["village_id"]),
                    new_village_id=new_id,
                    raw_village_text=old_entry.get("raw_village_text"),
                    qualifier_text=new_entry.get("qualifier_text"),
                    old_status=old_entry.get("village_match_status"),
                    new_status=new_entry.get("village_match_status"),
                    old_confidence=old_entry.get("village_confidence"),
                    new_confidence=new_entry.get("village_confidence"),
                )
            )
        return corrections, manual
    finally:
        db.rollback()
        db.close()


def correction_plan(
    correction: VillageCorrection,
    run_id: UUID,
) -> dict[str, Any]:
    return {
        "incident_id": correction.incident_id,
        "raw_message_id": correction.raw_message_id,
        "operation": "update_village",
        "is_deleted": correction.is_deleted,
        "raw_village_text": correction.raw_village_text,
        "qualifier_text": correction.qualifier_text,
        "changes": {
            "village_id": {
                "old": correction.old_village_id,
                "new": correction.new_village_id,
            },
            "match_status": {
                "old": correction.old_status,
                "new": correction.new_status,
            },
            "match_confidence": {
                "old": correction.old_confidence,
                "new": correction.new_confidence,
            },
        },
        "planned_incident_update_new_values": tagged_audit_values(
            {
                "village_id": correction.new_village_id,
                "backfill_operation": "village_correction",
                "raw_message_id": correction.raw_message_id,
            },
            run_id,
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", type=UUID)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    corrections, manual = discover_corrections()
    if args.limit is not None:
        corrections = corrections[: args.limit]
    run_id = args.run_id or uuid4()
    checkpoint = JsonlCheckpoint(
        args.output_dir / f"{PHASE}.checkpoint.jsonl",
        PHASE,
    )
    run_id, summary, results = run_batch(
        phase=PHASE,
        items=corrections,
        item_id=lambda item: item.incident_id,
        process=lambda item: correction_plan(item, run_id),
        checkpoint=checkpoint,
        run_id=run_id,
        progress_every=10,
    )
    write_dry_run_report(
        path=args.output_dir / f"{PHASE}.dry-run.json",
        phase=PHASE,
        run_id=run_id,
        summary=summary,
        results=results,
        metadata={
            "population": len(corrections),
            "population_a_excluded": True,
            "database_writes": False,
            "apply_implemented": False,
            "recon_cutoff": RECON_CUTOFF,
        },
    )
    write_json(
        args.output_dir / f"{PHASE}.manual-review.json",
        {"phase": PHASE, "items": manual},
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
