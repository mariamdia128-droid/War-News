from pathlib import Path
from uuid import UUID

from scripts.backfill.historical_incident_reconcile.common import (
    JsonlCheckpoint,
    run_batch,
    tagged_audit_values,
)


def test_run_batch_resumes_successful_items_without_double_processing(
    tmp_path: Path,
) -> None:
    checkpoint = JsonlCheckpoint(tmp_path / "phase0.jsonl", "phase0")
    called: list[int] = []

    def process(value: int) -> dict[str, int]:
        called.append(value)
        return {"value": value}

    _run_id, first, first_results = run_batch(
        phase="phase0",
        items=[1, 2],
        item_id=str,
        process=process,
        checkpoint=checkpoint,
        progress_every=0,
    )
    _run_id, second, second_results = run_batch(
        phase="phase0",
        items=[1, 2, 3],
        item_id=str,
        process=process,
        checkpoint=JsonlCheckpoint(tmp_path / "phase0.jsonl", "phase0"),
        progress_every=0,
    )

    assert called == [1, 2, 3]
    assert (first.processed, first.succeeded, first.failed) == (2, 2, 0)
    assert second.skipped_completed == 2
    assert second.processed == second.succeeded == 3
    assert first_results == [{"value": 1}, {"value": 2}]
    assert second_results == [
        {"value": 1},
        {"value": 2},
        {"value": 3},
    ]


def test_checkpoint_ignores_truncated_final_line(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.jsonl"
    path.write_text(
        '{"phase":"phase0","item_id":"1","run_id":"00000000-0000-0000-0000-000000000001",'
        '"completed_at":"now","result":{"ok":true}}\n{"phase":',
        encoding="utf-8",
    )

    checkpoint = JsonlCheckpoint(path, "phase0")

    assert checkpoint.completed_ids == frozenset({"1"})


def test_tagged_audit_values_adds_queryable_run_id() -> None:
    run_id = UUID("00000000-0000-0000-0000-000000000001")

    assert tagged_audit_values({"village_id": 2}, run_id) == {
        "village_id": 2,
        "backfill_run_id": str(run_id),
    }
