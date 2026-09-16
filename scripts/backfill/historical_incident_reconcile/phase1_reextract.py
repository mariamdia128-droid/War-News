#!/usr/bin/env python
"""Phase 1 dry run: re-extract and reconcile historical multi-village messages.

This module intentionally has no apply path. It calls the LLM and writes only
checkpoint/report files; every database transaction is explicitly read-only.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass
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
from app.api.factories.action_factory import build_extraction_classifier
from app.llm.dtos import ExtractionResult
from app.news.repositories.condition_repository import ConditionRepository
from app.news.repositories.incident_repository import IncidentRepository
from app.news.repositories.village_repository import VillageRepository
from app.news.services.dedup.story_continuation_router import (
    StoryContinuationRouter,
)
from app.news.services.materialization.incident_materialization_service import (
    IncidentMaterializationService,
)
from app.news.services.matching.matching_service import MatchingService
from scripts.backfill.historical_incident_reconcile.common import (
    DEFAULT_OUTPUT_DIR,
    JsonlCheckpoint,
    open_read_only_session,
    run_batch,
    tagged_audit_values,
    write_dry_run_report,
)

PHASE = "phase1_reextract"
ELIGIBLE_STATUSES = {"matched", "matched_low_confidence"}
RECON_CUTOFF = "2026-09-16T08:26:01Z"


@dataclass(frozen=True)
class RawCandidate:
    id: int
    raw_text: str
    status: str
    source_id: int
    message_datetime: Any
    content_embedding: list[float] | None
    old_extraction_result: dict[str, Any]
    old_match_result: dict[str, Any]


@dataclass(frozen=True)
class PlannedTarget:
    key: str
    ordinal: int
    village_id: int
    condition_id: int
    event_index: int | None
    raw_village_text: str | None
    raw_condition_text: str | None
    qualifier_text: str | None
    evidence_span: str | None
    village_match_status: str
    condition_match_status: str | None
    deaths: int | None
    injuries: int | None


def fetch_population(limit: int | None, only_ids: list[int]) -> list[RawCandidate]:
    db = open_read_only_session()
    try:
        rows = db.execute(
            text(
                """
                SELECT r.id, r.raw_text, r.status::text AS status, r.source_id,
                       r.message_datetime, r.content_embedding,
                       r.extraction_result, r.match_result
                FROM raw_messages r
                CROSS JOIN LATERAL jsonb_array_elements(
                  COALESCE(r.match_result->'village_matches', '[]'::jsonb)
                ) village(value)
                WHERE r.status::text IN ('parsed', 'materialized')
                  AND r.raw_text IS NOT NULL
                  AND COALESCE(r.materialized_at, r.matched_at, r.received_at)
                    <= CAST(:recon_cutoff AS timestamptz)
                  AND (:all_ids OR r.id = ANY(:only_ids))
                GROUP BY r.id
                HAVING count(
                  DISTINCT (village.value->>'matched_village_id')::int
                ) FILTER (
                  WHERE village.value->>'village_match_status'
                    IN ('matched', 'matched_low_confidence')
                    AND (village.value->>'matched_village_id') ~ '^[0-9]+$'
                ) > 1
                ORDER BY r.id
                """
            ),
            {
                "all_ids": not only_ids,
                "only_ids": only_ids or [0],
                "recon_cutoff": RECON_CUTOFF,
            },
        ).mappings()
        candidates = [
            RawCandidate(
                id=int(row["id"]),
                raw_text=str(row["raw_text"]),
                status=str(row["status"]),
                source_id=int(row["source_id"]),
                message_datetime=row["message_datetime"],
                content_embedding=(
                    list(row["content_embedding"])
                    if row["content_embedding"] is not None
                    else None
                ),
                old_extraction_result=dict(row["extraction_result"] or {}),
                old_match_result=dict(row["match_result"] or {}),
            )
            for row in rows
        ]
        return candidates[:limit] if limit is not None else candidates
    finally:
        db.rollback()
        db.close()


def build_targets(
    extraction: ExtractionResult,
    match_result: dict[str, Any],
) -> tuple[list[PlannedTarget], list[dict[str, Any]]]:
    targets: list[PlannedTarget] = []
    skipped: list[dict[str, Any]] = []
    root_condition = IncidentMaterializationService._optional_int(
        match_result.get("matched_condition_id")
    )
    for ordinal, village_match in enumerate(
        match_result.get("village_matches") or []
    ):
        role = village_match.get("village_role", "target")
        status = village_match.get("village_match_status")
        village_id = IncidentMaterializationService._optional_int(
            village_match.get("matched_village_id")
        )
        event_index = IncidentMaterializationService._optional_int(
            village_match.get("event_index")
        )
        condition_id = IncidentMaterializationService._optional_int(
            village_match.get("matched_condition_id")
        )
        if condition_id is None and event_index is None:
            condition_id = root_condition
        reason = None
        if role != "target":
            reason = "origin_role"
        elif status not in ELIGIBLE_STATUSES:
            reason = "village_not_materializable"
        elif village_id is None:
            reason = "missing_village_id"
        elif condition_id is None:
            reason = "missing_event_condition"
        if reason is not None:
            skipped.append(
                {
                    "ordinal": ordinal,
                    "reason": reason,
                    "match": village_match,
                }
            )
            continue

        is_multi = (
            len(
                {
                    item.get("matched_village_id")
                    for item in match_result.get("village_matches") or []
                    if item.get("village_role", "target") == "target"
                    and item.get("village_match_status") in ELIGIBLE_STATUSES
                    and isinstance(item.get("matched_village_id"), int)
                }
            )
            > 1
        )
        casualties = IncidentMaterializationService._casualties_for_village(
            extraction,
            village_match,
            is_multi_village=is_multi,
        )
        targets.append(
            PlannedTarget(
                key=(
                    f"{event_index if event_index is not None else 'root'}:"
                    f"{village_id}:{condition_id}:{ordinal}"
                ),
                ordinal=ordinal,
                village_id=village_id,
                condition_id=condition_id,
                event_index=event_index,
                raw_village_text=village_match.get("raw_village_text"),
                raw_condition_text=village_match.get("raw_condition_text"),
                qualifier_text=village_match.get("qualifier_text"),
                evidence_span=village_match.get("evidence_span"),
                village_match_status=str(status),
                condition_match_status=village_match.get(
                    "condition_match_status"
                ),
                deaths=casualties.deaths,
                injuries=casualties.injuries,
            )
        )
    return targets, skipped


def _canonical_score(incident: dict[str, Any]) -> tuple[int, str]:
    score = int(incident.get("human_update_count") or 0) * 100
    if incident.get("verification_status") == "verified":
        score += 1000
    for key in (
        "deaths",
        "injuries",
        "total_deaths",
        "total_injuries",
        "martyrs",
        "note",
    ):
        if incident.get(key) is not None:
            score += 1
    return score, str(incident["id"])


def _append_note(old_note: str | None, qualifier: str | None) -> str | None:
    if not qualifier or not qualifier.strip():
        return old_note
    addition = f"Location qualifier: {qualifier.strip()}"
    if addition in (old_note or ""):
        return old_note
    return f"{old_note}\n{addition}" if old_note else addition


def reconcile_direct_incidents(
    *,
    raw_message_id: int,
    targets: list[PlannedTarget],
    incidents: list[dict[str, Any]],
    run_id: UUID,
    raw_text: str,
) -> list[dict[str, Any]]:
    """Create a deterministic, review-only operation plan."""
    active = [item for item in incidents if not item["is_deleted"]]
    operations: list[dict[str, Any]] = []
    unused = {str(item["id"]): item for item in active}
    matched_incident_by_target: dict[str, dict[str, Any]] = {}

    for target in targets:
        exact = [
            item
            for item in unused.values()
            if item["village_id"] == target.village_id
            and item["condition_id"] == target.condition_id
        ]
        same_village = [
            item
            for item in unused.values()
            if item["village_id"] == target.village_id
        ]
        candidates = exact or same_village
        if not candidates:
            continue
        chosen = max(candidates, key=_canonical_score)
        unused.pop(str(chosen["id"]))
        matched_incident_by_target[target.key] = chosen
        new_note = _append_note(chosen.get("note"), target.qualifier_text)
        changes: dict[str, dict[str, Any]] = {}
        if chosen["condition_id"] != target.condition_id:
            changes["condition_id"] = {
                "old": chosen["condition_id"],
                "new": target.condition_id,
            }
        if new_note != chosen.get("note"):
            changes["note"] = {"old": chosen.get("note"), "new": new_note}
        operations.append(
            {
                "operation": "update" if changes else "keep",
                "incident_id": str(chosen["id"]),
                "target_key": target.key,
                "changes": changes,
                "preserve_fields": [
                    "id",
                    "human audit history",
                    "human comments",
                    "casualties",
                    "verification outcome",
                ],
                "human_touched": bool(
                    chosen.get("human_update_count")
                    or chosen.get("created_by")
                    or chosen.get("verified_by_user_id")
                ),
                "planned_incident_update_new_values": (
                    tagged_audit_values(
                        {
                            key: value["new"]
                            for key, value in changes.items()
                        },
                        run_id,
                    )
                    if changes
                    else None
                ),
            }
        )

    unmatched_targets = [
        target for target in targets if target.key not in matched_incident_by_target
    ]
    for target in unmatched_targets:
        operations.append(
            {
                "operation": "new",
                "target_key": target.key,
                "incident_id": None,
                "new_values": {
                    "raw_message_id": raw_message_id,
                    "village_id": target.village_id,
                    "condition_id": target.condition_id,
                    "khabar": raw_text,
                    "deaths": target.deaths,
                    "injuries": target.injuries,
                    "note": _append_note(None, target.qualifier_text),
                },
                "planned_incident_update_new_values": tagged_audit_values(
                    {
                        "backfill_operation": "create",
                        "raw_message_id": raw_message_id,
                        "village_id": target.village_id,
                        "condition_id": target.condition_id,
                    },
                    run_id,
                ),
            }
        )

    route_like = "طريق" in raw_text and any(
        marker in raw_text for marker in ("-", "–", "—")
    )
    surviving = [
        item
        for item in matched_incident_by_target.values()
        if not item["is_deleted"]
    ]
    for incident in unused.values():
        merge_target = (
            max(surviving, key=_canonical_score)
            if route_like and surviving
            else None
        )
        if merge_target is not None:
            operation = "merge"
            reason = "route_story_equivalence"
            canonical_id = str(merge_target["id"])
        else:
            operation = "soft_delete"
            reason = "no_corresponding_fixed_pipeline_target"
            canonical_id = None
        operations.append(
            {
                "operation": operation,
                "incident_id": str(incident["id"]),
                "canonical_incident_id": canonical_id,
                "reason": reason,
                "changes": {"is_deleted": {"old": False, "new": True}},
                "planned_incident_update_new_values": tagged_audit_values(
                    {
                        "is_deleted": True,
                        "backfill_operation": operation,
                        "reason": reason,
                        "canonical_incident_id": canonical_id,
                    },
                    run_id,
                ),
            }
        )
    return operations


def _incident_snapshots(db: Any, raw_message_id: int) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT i.*,
                  (
                    SELECT count(*) FROM incident_updates iu
                    WHERE iu.incident_id = i.id AND iu.performed_by IS NOT NULL
                  ) AS human_update_count
                FROM incidents i
                WHERE i.raw_message_id = :raw_message_id
                ORDER BY i.created_at, i.id
                """
            ),
            {"raw_message_id": raw_message_id},
        ).mappings()
    ]


class Phase1Processor:
    def __init__(self, run_id: UUID) -> None:
        aliases_db = open_read_only_session()
        try:
            aliases = VillageRepository(aliases_db).casualty_scope_aliases()
        finally:
            aliases_db.rollback()
            aliases_db.close()
        classifier = build_extraction_classifier(
            casualty_scope_aliases=aliases
        )
        self.extractor = getattr(classifier, "fallback", classifier)
        self.run_id = run_id

    def __call__(self, candidate: RawCandidate) -> dict[str, Any]:
        combined = getattr(self.extractor, "_extract_tier1_combined", None)
        if combined is None:
            raise RuntimeError(
                "Configured extractor does not expose fixed combined Tier-1"
            )
        extraction = combined(
            candidate.raw_text,
            raw_message_id=candidate.id,
        )
        db = open_read_only_session()
        try:
            match = MatchingService(
                VillageRepository(db),
                ConditionRepository(db),
            ).match(extraction)
            match_payload = match.model_dump(mode="json")
            targets, skipped = build_targets(extraction, match_payload)
            incidents = _incident_snapshots(db, candidate.id)
            operations = reconcile_direct_incidents(
                raw_message_id=candidate.id,
                targets=targets,
                incidents=incidents,
                run_id=self.run_id,
                raw_text=candidate.raw_text,
            )

            external_routes: list[dict[str, Any]] = []
            router = StoryContinuationRouter(IncidentRepository(db))
            direct_target_keys = {
                operation.get("target_key")
                for operation in operations
                if operation["operation"] in {"keep", "update"}
            }
            for target in targets:
                if target.key in direct_target_keys:
                    continue
                route = router.route_for_village(
                    match_result=match_payload,
                    message_datetime=candidate.message_datetime,
                    candidate_text=target.evidence_span or candidate.raw_text,
                    candidate_embedding=candidate.content_embedding,
                    exclude_raw_message_id=candidate.id,
                    village_id=target.village_id,
                )
                if route is not None:
                    external_routes.append(
                        {
                            "target_key": target.key,
                            "relationship": route.relationship.value,
                            "candidate_incident_id": str(route.candidate.id),
                            "candidate_raw_message_id": route.candidate.raw_message_id,
                            "evidence": route.classification.relationship_evidence,
                            "needs_review": route.classification.needs_review,
                        }
                    )
            return {
                "raw_message_id": candidate.id,
                "status": candidate.status,
                "old_extraction": candidate.old_extraction_result,
                "new_extraction": extraction.model_dump(mode="json"),
                "old_match_result": candidate.old_match_result,
                "new_match_result": match_payload,
                "targets": [asdict(target) for target in targets],
                "skipped_matches": skipped,
                "existing_incidents": incidents,
                "operations": operations,
                "external_story_routes": external_routes,
                "requires_manual_review": not incidents,
            }
        finally:
            db.rollback()
            db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--raw-message-id",
        type=int,
        action="append",
        default=[],
        dest="raw_message_ids",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", type=UUID)
    parser.add_argument("--progress-every", type=int, default=1)
    args = parser.parse_args()

    candidates = fetch_population(args.limit, args.raw_message_ids)
    run_id = args.run_id or uuid4()
    checkpoint = JsonlCheckpoint(
        args.output_dir / f"{PHASE}.checkpoint.jsonl",
        PHASE,
    )
    processor = Phase1Processor(run_id)
    run_id, summary, results = run_batch(
        phase=PHASE,
        items=candidates,
        item_id=lambda item: str(item.id),
        process=processor,
        checkpoint=checkpoint,
        run_id=run_id,
        progress_every=args.progress_every,
    )
    write_dry_run_report(
        path=args.output_dir / f"{PHASE}.dry-run.json",
        phase=PHASE,
        run_id=run_id,
        summary=summary,
        results=results,
        metadata={
            "population": len(candidates),
            "database_writes": False,
            "apply_implemented": False,
            "population_rule": (
                "parsed/materialized raw messages with >1 distinct matched "
                "village across target and origin roles"
            ),
            "extraction_mode": "fixed_combined_tier1_one_call",
            "recon_cutoff": RECON_CUTOFF,
        },
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
