"""Shared, write-safe batch primitives for historical reconciliation dry runs."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timezone
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

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
    url = os.environ.get("DATABASE_URL", settings.database_url)
    if "@db:" in url and not Path("/.dockerenv").exists():
        url = url.replace(
            "@db:5432",
            f"@localhost:{os.environ.get('POSTGRES_HOST_PORT', '5432')}",
        )
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
        lines = self.path.read_text(encoding="utf-8").splitlines(
            keepends=True
        )
        for index, line in enumerate(lines):
            try:
                payload = json.loads(line)
                record = CheckpointRecord(**payload)
            except (json.JSONDecodeError, TypeError) as exc:
                is_truncated_last_line = (
                    index == len(lines) - 1 and not line.endswith(("\n", "\r"))
                )
                if is_truncated_last_line:
                    continue
                raise RuntimeError(
                    f"Corrupt checkpoint record at {self.path}:{index + 1}"
                ) from exc
            if record.phase != self.phase:
                raise RuntimeError(
                    f"Checkpoint phase mismatch at {self.path}:{index + 1}: "
                    f"expected {self.phase!r}, got {record.phase!r}"
                )
            completed[record.item_id] = record
        return completed

    def resolve_run_id(self, requested: UUID | None = None) -> UUID:
        existing_ids = {record.run_id for record in self._completed.values()}
        if len(existing_ids) > 1:
            raise RuntimeError(
                f"Checkpoint {self.path} mixes logical run IDs: "
                f"{sorted(existing_ids)}"
            )
        if existing_ids:
            existing = UUID(next(iter(existing_ids)))
            if requested is not None and requested != existing:
                raise RuntimeError(
                    f"Checkpoint {self.path} belongs to run {existing}; "
                    f"requested {requested}"
                )
            return existing
        return requested or uuid4()

    @property
    def failure_path(self) -> Path:
        return self.path.with_name(
            self.path.name.replace(".checkpoint.jsonl", ".failures.jsonl")
        )

    @property
    def lock_path(self) -> Path:
        return self.path.with_suffix(self.path.suffix + ".lock")

    @contextmanager
    def exclusive_run(self) -> Any:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(
                self.lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as exc:
            raise RuntimeError(
                f"Checkpoint is already in use or has a stale lock: "
                f"{self.lock_path}"
            ) from exc
        try:
            os.write(
                descriptor,
                f"pid={os.getpid()} started_at={utc_now()}\n".encode("utf-8"),
            )
            os.close(descriptor)
            yield
        finally:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass

    def append_failure(
        self,
        *,
        item_id: str,
        run_id: UUID,
        error: Exception,
    ) -> None:
        self.failure_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "phase": self.phase,
            "item_id": item_id,
            "run_id": str(run_id),
            "failed_at": utc_now(),
            "error_type": type(error).__name__,
            "error": str(error),
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        with self.failure_path.open(
            "a", encoding="utf-8", newline="\n"
        ) as handle:
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())

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
    invocation_run_id = checkpoint.resolve_run_id(run_id)
    summary = BatchSummary()
    ordered_results: list[dict[str, Any]] = []
    with checkpoint.exclusive_run():
        for item in items:
            key = item_id(item)
            summary.processed += 1
            previous = checkpoint.result_for(key)
            if previous is not None:
                summary.skipped_completed += 1
                summary.succeeded += 1
                ordered_results.append(previous)
                continue

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
                checkpoint.append_failure(
                    item_id=key,
                    run_id=invocation_run_id,
                    error=exc,
                )
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
