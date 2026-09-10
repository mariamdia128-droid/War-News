from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.news.models import MessageStatus, RawMessage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DedupOriginalReconciliationResult:
    original_id: int
    promoted_id: int | None
    relinked_count: int


class OrphanedDedupOriginalReconciliationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def reconcile(
        self,
        *,
        max_groups: int | None = None,
        max_retries: int | None = None,
    ) -> list[DedupOriginalReconciliationResult]:
        retry_limit = (
            max_retries if max_retries is not None else settings.extraction_max_retries
        )
        original_ids = self.dead_original_ids(
            retry_limit=retry_limit,
            limit=max_groups,
        )
        results: list[DedupOriginalReconciliationResult] = []
        for original_id in original_ids:
            results.append(
                self.reconcile_original(
                    original_id,
                    retry_limit=retry_limit,
                )
            )
        return results

    def reconcile_original(
        self,
        original_id: int,
        *,
        retry_limit: int,
    ) -> DedupOriginalReconciliationResult:
        original = self.db.get(RawMessage, original_id)
        if (
            original is None
            or original.status != MessageStatus.error
            or original.extraction_retry_count < retry_limit
        ):
            return DedupOriginalReconciliationResult(
                original_id=original_id,
                promoted_id=None,
                relinked_count=0,
            )

        children = self._duplicate_children(original_id)
        if not children:
            return DedupOriginalReconciliationResult(
                original_id=original_id,
                promoted_id=None,
                relinked_count=0,
            )

        promoted = children[0]
        note = (
            f"Promoted from dead original raw_message #{original_id}: "
            "exhausted retries with status=error"
        )
        promoted.status = MessageStatus.parsed
        promoted.duplicate_of_id = None
        promoted.error_message = None
        promoted.dedup_promotion_note = note
        self._clear_processing_claim(promoted)
        self.db.add(promoted)

        relinked_count = 0
        for sibling in children[1:]:
            sibling.duplicate_of_id = promoted.id
            sibling.dedup_promotion_note = note
            self._clear_processing_claim(sibling)
            self.db.add(sibling)
            relinked_count += 1

        self.db.commit()
        logger.info(
            "Reconciled dead dedup original raw_message_id=%s promoted_id=%s "
            "relinked_count=%s",
            original_id,
            promoted.id,
            relinked_count,
        )
        return DedupOriginalReconciliationResult(
            original_id=original_id,
            promoted_id=promoted.id,
            relinked_count=relinked_count,
        )

    def dead_original_ids(
        self,
        *,
        retry_limit: int,
        limit: int | None,
    ) -> list[int]:
        duplicate = RawMessage.__table__.alias("duplicate_raw_messages")
        original = RawMessage.__table__.alias("original_raw_messages")
        stmt = (
            select(original.c.id)
            .select_from(
                duplicate.join(original, original.c.id == duplicate.c.duplicate_of_id)
            )
            .where(
                duplicate.c.status == MessageStatus.duplicate.value,
                original.c.status == MessageStatus.error.value,
                original.c.extraction_retry_count >= retry_limit,
            )
            .group_by(original.c.id)
            .order_by(original.c.id.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return [int(value) for value in self.db.scalars(stmt).all()]

    def _duplicate_children(self, original_id: int) -> list[RawMessage]:
        sort_datetime = (
            RawMessage.message_datetime.is_(None),
            RawMessage.message_datetime.asc(),
        )
        return list(
            self.db.scalars(
                select(RawMessage)
                .where(
                    RawMessage.status == MessageStatus.duplicate,
                    RawMessage.duplicate_of_id == original_id,
                )
                .order_by(*sort_datetime, RawMessage.id.asc())
            ).all()
        )

    @staticmethod
    def _clear_processing_claim(message: RawMessage) -> None:
        message.processing_claim_stage = None
        message.processing_claimed_at = None
        message.processing_claimed_by = None
