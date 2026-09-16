from pathlib import Path
from uuid import UUID

import scripts.backfill.historical_incident_reconcile.phase1_reextract as phase1
from scripts.backfill.historical_incident_reconcile.phase1_reextract import (
    PlannedTarget,
    RawCandidate,
    load_or_create_population_manifest,
    reconcile_direct_incidents,
)

RUN_ID = UUID("00000000-0000-0000-0000-000000000001")


def _target(
    key: str,
    village_id: int,
    condition_id: int,
    qualifier: str | None = None,
) -> PlannedTarget:
    return PlannedTarget(
        key=key,
        ordinal=0,
        village_id=village_id,
        condition_id=condition_id,
        event_index=0,
        raw_village_text="village",
        raw_condition_text="action",
        qualifier_text=qualifier,
        evidence_span="evidence",
        village_match_status="matched",
        condition_match_status="matched",
        deaths=None,
        injuries=None,
    )


def _incident(
    incident_id: str,
    village_id: int,
    condition_id: int,
    **overrides: object,
) -> dict:
    value = {
        "id": incident_id,
        "village_id": village_id,
        "condition_id": condition_id,
        "is_deleted": False,
        "note": None,
        "human_update_count": 0,
        "verification_status": "auto_processed",
        "created_by": None,
        "verified_by_user_id": None,
        "deaths": None,
        "injuries": None,
        "total_deaths": None,
        "total_injuries": None,
        "martyrs": None,
    }
    value.update(overrides)
    return value


def test_reconcile_updates_same_village_in_place_and_preserves_history() -> None:
    operations = reconcile_direct_incidents(
        raw_message_id=10,
        targets=[_target("0:1:8:0", 1, 8, "قضاء بنت جبيل")],
        incidents=[
            _incident(
                "00000000-0000-0000-0000-000000000010",
                1,
                5,
                human_update_count=2,
            )
        ],
        run_id=RUN_ID,
        raw_text="report",
    )

    assert len(operations) == 1
    operation = operations[0]
    assert operation["operation"] == "update"
    assert operation["incident_id"].endswith("0010")
    assert operation["changes"]["condition_id"] == {"old": 5, "new": 8}
    assert operation["changes"]["note"]["new"] == (
        "Location qualifier: قضاء بنت جبيل"
    )
    assert operation["human_touched"] is True
    assert (
        operation["planned_incident_update_new_values"]["backfill_run_id"]
        == str(RUN_ID)
    )


def test_reconcile_soft_deletes_cartesian_extra_and_creates_missing_target() -> None:
    operations = reconcile_direct_incidents(
        raw_message_id=10,
        targets=[
            _target("0:1:8:0", 1, 8),
            _target("1:2:9:1", 2, 9),
        ],
        incidents=[
            _incident("a", 1, 8),
            _incident("b", 3, 8),
        ],
        run_id=RUN_ID,
        raw_text="report",
    )

    by_operation = {item["operation"]: item for item in operations}
    assert by_operation["keep"]["incident_id"] == "a"
    assert by_operation["new"]["new_values"]["village_id"] == 2
    assert by_operation["soft_delete"]["incident_id"] == "b"
    assert by_operation["soft_delete"]["changes"]["is_deleted"] == {
        "old": False,
        "new": True,
    }


def test_route_like_unmatched_incident_requires_global_merge_review() -> None:
    operations = reconcile_direct_incidents(
        raw_message_id=10,
        targets=[_target("0:1:8:0", 1, 8)],
        incidents=[_incident("canonical", 1, 8), _incident("retired", 2, 8)],
        run_id=RUN_ID,
        raw_text="على طريق حاروف - زبدين",
    )

    merge = next(
        item for item in operations if item["operation"] == "route_merge_review"
    )
    assert merge["incident_id"] == "retired"
    assert merge["canonical_incident_id"] == "canonical"
    assert merge["reason"] == (
        "route_story_equivalence_requires_global_reconciliation"
    )
    assert merge["planned_incident_update_new_values"] is None


def test_population_manifest_freezes_ids_across_resume(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidates = [
        RawCandidate(
            id=10,
            raw_text="text",
            status="materialized",
            source_id=1,
            message_datetime=None,
            content_embedding=None,
            cnrs_classification=None,
            old_extraction_result={},
            old_match_result={},
        )
    ]
    monkeypatch.setattr(phase1, "fetch_population", lambda *_args: candidates)

    path, first = load_or_create_population_manifest(tmp_path)
    monkeypatch.setattr(
        phase1,
        "fetch_population",
        lambda *_args: (_ for _ in ()).throw(AssertionError("recomputed")),
    )
    resumed_path, resumed = load_or_create_population_manifest(tmp_path)

    assert path == resumed_path
    assert first == resumed == [10]
