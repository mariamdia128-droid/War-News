from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.news.models import MessageStatus
from app.news.services.dedup.orphaned_dedup_original_reconciliation import (
    OrphanedDedupOriginalReconciliationService,
)


class _SessionStub:
    def __init__(self, messages: dict[int, SimpleNamespace]) -> None:
        self.messages = messages
        self.added: list[SimpleNamespace] = []
        self.commit_calls = 0
        self.rollback_calls = 0

    def get(self, _model, pk: int):
        return self.messages.get(pk)

    def add(self, value: SimpleNamespace) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


class _ServiceStub(OrphanedDedupOriginalReconciliationService):
    def dead_original_ids(self, *, retry_limit: int, limit: int | None) -> list[int]:
        ids = sorted(
            {
                message.duplicate_of_id
                for message in self.db.messages.values()
                if message.status == MessageStatus.duplicate
                and message.duplicate_of_id is not None
                and (
                    original := self.db.messages.get(message.duplicate_of_id)
                ) is not None
                and original.status == MessageStatus.error
                and original.extraction_retry_count >= retry_limit
            }
        )
        return ids[:limit] if limit is not None else ids

    def _duplicate_children(self, original_id: int) -> list[SimpleNamespace]:
        children = [
            message
            for message in self.db.messages.values()
            if message.status == MessageStatus.duplicate
            and message.duplicate_of_id == original_id
        ]
        return sorted(
            children,
            key=lambda message: (
                message.message_datetime is None,
                message.message_datetime or datetime.max.replace(tzinfo=timezone.utc),
                message.id,
            ),
        )


def _message(
    id_: int,
    *,
    status: MessageStatus,
    duplicate_of_id: int | None = None,
    retry_count: int = 0,
    message_datetime: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id_,
        status=status,
        duplicate_of_id=duplicate_of_id,
        extraction_retry_count=retry_count,
        error_message="existing error",
        dedup_promotion_note=None,
        processing_claim_stage="tier1_extraction",
        processing_claimed_at="claimed-now",
        processing_claimed_by="worker-1",
        message_datetime=message_datetime,
    )


def test_reconciles_three_duplicate_group_to_earliest_viable_duplicate() -> None:
    dead = _message(100, status=MessageStatus.error, retry_count=5)
    later = _message(
        201,
        status=MessageStatus.duplicate,
        duplicate_of_id=100,
        message_datetime=datetime(2026, 9, 10, 8, 45, tzinfo=timezone.utc),
    )
    earliest = _message(
        202,
        status=MessageStatus.duplicate,
        duplicate_of_id=100,
        message_datetime=datetime(2026, 9, 10, 8, 30, tzinfo=timezone.utc),
    )
    tied_later_id = _message(
        203,
        status=MessageStatus.duplicate,
        duplicate_of_id=100,
        message_datetime=datetime(2026, 9, 10, 8, 30, tzinfo=timezone.utc),
    )
    db = _SessionStub({100: dead, 201: later, 202: earliest, 203: tied_later_id})

    results = _ServiceStub(db).reconcile(max_retries=5)

    assert len(results) == 1
    assert results[0].original_id == 100
    assert results[0].promoted_id == 202
    assert results[0].relinked_count == 2
    assert earliest.status == MessageStatus.parsed
    assert earliest.duplicate_of_id is None
    assert earliest.error_message is None
    assert earliest.processing_claim_stage is None
    assert later.duplicate_of_id == 202
    assert tied_later_id.duplicate_of_id == 202
    assert "dead original raw_message #100" in (earliest.dedup_promotion_note or "")
    assert later.dedup_promotion_note == earliest.dedup_promotion_note


def test_single_duplicate_child_is_promoted_without_relinks() -> None:
    dead = _message(100, status=MessageStatus.error, retry_count=5)
    child = _message(201, status=MessageStatus.duplicate, duplicate_of_id=100)
    db = _SessionStub({100: dead, 201: child})

    results = _ServiceStub(db).reconcile(max_retries=5)

    assert results[0].promoted_id == 201
    assert results[0].relinked_count == 0
    assert child.status == MessageStatus.parsed
    assert child.duplicate_of_id is None


def test_second_reconciliation_run_is_noop() -> None:
    dead = _message(100, status=MessageStatus.error, retry_count=5)
    child = _message(201, status=MessageStatus.duplicate, duplicate_of_id=100)
    service = _ServiceStub(_SessionStub({100: dead, 201: child}))

    first = service.reconcile(max_retries=5)
    second = service.reconcile(max_retries=5)

    assert first[0].promoted_id == 201
    assert second == []


def test_original_under_retry_cap_is_not_touched() -> None:
    original = _message(100, status=MessageStatus.error, retry_count=4)
    child = _message(201, status=MessageStatus.duplicate, duplicate_of_id=100)
    db = _SessionStub({100: original, 201: child})

    results = _ServiceStub(db).reconcile(max_retries=5)

    assert results == []
    assert child.status == MessageStatus.duplicate
    assert child.duplicate_of_id == 100
    assert db.commit_calls == 0


def test_non_error_original_statuses_are_out_of_scope() -> None:
    materialized = _message(100, status=MessageStatus.materialized, retry_count=5)
    parsed = _message(200, status=MessageStatus.parsed, retry_count=5)
    materialized_child = _message(
        101,
        status=MessageStatus.duplicate,
        duplicate_of_id=100,
    )
    parsed_child = _message(201, status=MessageStatus.duplicate, duplicate_of_id=200)
    db = _SessionStub(
        {
            100: materialized,
            101: materialized_child,
            200: parsed,
            201: parsed_child,
        }
    )

    results = _ServiceStub(db).reconcile(max_retries=5)

    assert results == []
    assert materialized_child.duplicate_of_id == 100
    assert parsed_child.duplicate_of_id == 200
    assert materialized_child.status == MessageStatus.duplicate
    assert parsed_child.status == MessageStatus.duplicate
