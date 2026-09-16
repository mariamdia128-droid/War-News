#!/usr/bin/env python
"""Phase 3 dry run: report no-op toll revisions to suppress from history."""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from scripts.backfill.historical_incident_reconcile.common import (
    DEFAULT_OUTPUT_DIR,
    JsonlCheckpoint,
    open_read_only_session,
    run_batch,
    tagged_audit_values,
    write_dry_run_report,
)
from scripts.backfill.historical_incident_reconcile.phase1_reextract import (
    RECON_CUTOFF,
)

PHASE = "phase3_toll"


@dataclass(frozen=True)
class TollIncident:
    incident_id: str
    is_deleted: bool
    rows: tuple[dict[str, Any], ...]


def effective_casualties(values: dict[str, Any] | None) -> tuple[int | None, int | None]:
    payload = values or {}

    def first_integer(*keys: str) -> int | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        return None

    return (
        first_integer("total_deaths", "deaths"),
        first_integer("total_injuries", "injuries"),
    )


def fetch_population() -> list[TollIncident]:
    db = open_read_only_session()
    try:
        rows = db.execute(
            text(
                """
                SELECT iu.id AS update_id, iu.incident_id::text AS incident_id,
                       iu.created_at, iu.old_values, iu.new_values,
                       i.is_deleted
                FROM incident_updates iu
                JOIN incidents i ON i.id = iu.incident_id
                WHERE iu.action::text = 'pipeline_merge'
                  AND iu.new_values->>'story_revision' = 'true'
                  AND iu.created_at <= CAST(:recon_cutoff AS timestamptz)
                ORDER BY iu.incident_id, iu.created_at, iu.id
                """
            ),
            {"recon_cutoff": RECON_CUTOFF},
        ).mappings()
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        deleted: dict[str, bool] = {}
        for row in rows:
            old_values = dict(row["old_values"] or {})
            new_values = dict(row["new_values"] or {})
            old_effective = effective_casualties(old_values)
            new_effective = effective_casualties(new_values)
            if old_effective != new_effective:
                continue
            incident_id = str(row["incident_id"])
            grouped[incident_id].append(
                {
                    "update_id": int(row["update_id"]),
                    "created_at": row["created_at"],
                    "old_values": old_values,
                    "new_values": new_values,
                    "old_effective": {
                        "deaths": old_effective[0],
                        "injuries": old_effective[1],
                    },
                    "new_effective": {
                        "deaths": new_effective[0],
                        "injuries": new_effective[1],
                    },
                    "strict_raw_casualty_fields_equal": all(
                        old_values.get(key) == new_values.get(key)
                        for key in (
                            "deaths",
                            "total_deaths",
                            "injuries",
                            "total_injuries",
                        )
                    ),
                    "source": new_values.get("merged_from"),
                }
            )
            deleted[incident_id] = bool(row["is_deleted"])
        return [
            TollIncident(
                incident_id=incident_id,
                is_deleted=deleted[incident_id],
                rows=tuple(items),
            )
            for incident_id, items in sorted(grouped.items())
        ]
    finally:
        db.rollback()
        db.close()


def toll_plan(item: TollIncident, run_id: UUID) -> dict[str, Any]:
    return {
        "incident_id": item.incident_id,
        "is_deleted": item.is_deleted,
        "operation": "suppress_noop_toll_revisions",
        "row_count": len(item.rows),
        "rows": list(item.rows),
        "surface_diff": {
            "old": [row["update_id"] for row in item.rows],
            "new": [],
        },
        "database_row_action": "none",
        "reason": (
            "Current toll_revisions projection already suppresses rows whose "
            "effective old/new death and injury pairs are equal. Audit rows "
            "remain intact."
        ),
        "future_audit_payload_if_state_changes": tagged_audit_values(
            {
                "backfill_operation": "suppress_noop_toll_revisions",
                "suppressed_update_ids": [
                    row["update_id"] for row in item.rows
                ],
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

    population = fetch_population()
    if args.limit is not None:
        population = population[: args.limit]
    checkpoint = JsonlCheckpoint(
        args.output_dir / f"{PHASE}.checkpoint.jsonl",
        PHASE,
    )
    run_id = checkpoint.resolve_run_id(args.run_id)
    run_id, summary, results = run_batch(
        phase=PHASE,
        items=population,
        item_id=lambda item: item.incident_id,
        process=lambda item: toll_plan(item, run_id),
        checkpoint=checkpoint,
        run_id=run_id,
        progress_every=25,
    )
    write_dry_run_report(
        path=args.output_dir / f"{PHASE}.dry-run.json",
        phase=PHASE,
        run_id=run_id,
        summary=summary,
        results=results,
        metadata={
            "population": len(population),
            "no_op_rows": sum(len(item.rows) for item in population),
            "database_writes": False,
            "apply_implemented": False,
            "actual_apply_sequence": [
                "phase1_reextract",
                "phase2_village",
                "phase3_toll",
            ],
            "recon_cutoff": RECON_CUTOFF,
        },
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
