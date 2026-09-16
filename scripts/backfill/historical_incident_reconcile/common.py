"""Shared, write-safe batch primitives for historical reconciliation dry runs."""
from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timezone
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg2://postgres:secret@localhost:5432/war_news_dev"
)
DEFAULT_OUTPUT_DIR = Path("scripts/output/historical_incident_reconcile")

T = TypeVar("T")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_default(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Cannot JSON-serialize {type(value).__name__}")


def open_read_only_session() -> Session:
    """Open a database session whose transaction cannot write."""
    url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    if "@db:" in url and not Path("/.dockerenv").exists():
        url = url.replace("@db:", "@localhost:")
    db = sessionmaker(bind=create_engine(url))()
    db.execute(
        text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    )
    return db


def tagged_audit_values(values: dict[str, Any], run_id: UUID) -> dict[str, Any]:
    """Return the future audit payload represented by a dry-run operation."""
    return {**values, "backfill_run_id": str(run_id)}


@dataclass
class BatchSummary:
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped_completed: int = 0


@dataclass(frozen=True)
class CheckpointRecord:
    phase: str
    item_id: str
    run_id: str
    completed_at: str
    result: dict[str, Any]


class JsonlCheckpoint:
    """Append-only successful-item checkpoint.

    A truncated final line is ignored so interruption during one append never
    invalidates earlier completed work.
    """

    def __init__(self, path: Path, phase: str) -> None:
        self.path = path
        self.phase = phase
        self._completed = self._load()

    def _load(self) -> dict[str, CheckpointRecord]:
        completed: dict[str, CheckpointRecord] = {}
        if not self.path.exists():
            return completed
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    payload = json.loads(line)
                    record = CheckpointRecord(**payload)
                except (json.JSONDecodeError, TypeError):
                    continue
                if record.phase == self.phase:
                    completed[record.item_id] = record
        return completed

    @property
    def completed_ids(self) -> frozenset[str]:
        return frozenset(self._completed)

    def result_for(self, item_id: str) -> dict[str, Any] | None:
        record = self._completed.get(item_id)
        return record.result if record is not None else None

    def append_success(
        self,
        *,
        item_id: str,
        run_id: UUID,
        result: dict[str, Any],
    ) -> None:
        record = CheckpointRecord(
            phase=self.phase,
            item_id=item_id,
            run_id=str(run_id),
            completed_at=utc_now(),
            result=result,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(
            asdict(record),
            ensure_ascii=False,
            default=json_default,
            separators=(",", ":"),
        )
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._completed[item_id] = record


def write_json(path: Path, payload: Any) -> None:
    """Atomically replace a review artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=json_default,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def run_batch(
    *,
    phase: str,
    items: Iterable[T],
    item_id: Callable[[T], str],
    process: Callable[[T], dict[str, Any]],
    checkpoint: JsonlCheckpoint,
    run_id: UUID | None = None,
    progress_every: int = 10,
) -> tuple[UUID, BatchSummary, list[dict[str, Any]]]:
    """Process missing items and return all checkpointed results in input order."""
    invocation_run_id = run_id or uuid4()
    summary = BatchSummary()
    ordered_results: list[dict[str, Any]] = []
    for item in items:
        key = item_id(item)
        previous = checkpoint.result_for(key)
        if previous is not None:
            summary.skipped_completed += 1
            ordered_results.append(previous)
            continue

        summary.processed += 1
        try:
            result = process(item)
            checkpoint.append_success(
                item_id=key,
                run_id=invocation_run_id,
                result=result,
            )
            ordered_results.append(result)
            summary.succeeded += 1
        except Exception as exc:
            summary.failed += 1
            print(
                f"{phase} item_id={key} failed: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
        if progress_every > 0 and summary.processed % progress_every == 0:
            print(
                f"{phase} progress: processed={summary.processed} "
                f"succeeded={summary.succeeded} failed={summary.failed} "
                f"skipped_completed={summary.skipped_completed}",
                flush=True,
            )
    print(
        f"{phase} completed: processed={summary.processed} "
        f"succeeded={summary.succeeded} failed={summary.failed} "
        f"skipped_completed={summary.skipped_completed}",
        flush=True,
    )
    return invocation_run_id, summary, ordered_results


def write_dry_run_report(
    *,
    path: Path,
    phase: str,
    run_id: UUID,
    summary: BatchSummary,
    results: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> None:
    write_json(
        path,
        {
            "mode": "dry_run",
            "phase": phase,
            "backfill_run_id": str(run_id),
            "generated_at": utc_now(),
            "summary": asdict(summary),
            "metadata": metadata or {},
            "items": results,
        },
    )
