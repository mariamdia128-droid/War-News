from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.news.models import MatchStatus
from app.news.repositories.incident_repository import SegmentReviewSource
from app.news.services.dedup.segment_review_dedup import SegmentReviewDedupService


class _DbStub:
    def __init__(self) -> None:
        self.commit_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1


class _IncidentRepositoryStub:
    def __init__(self, source: SegmentReviewSource, score: float) -> None:
        self.source = source
        self.score = score
        self.db = _DbStub()
        self.created: list[dict] = []
        self.query: dict | None = None

    def find_segment_review_sources(self, **kwargs):
        self.query = kwargs
        return [self.source]

    def segment_text_similarity(self, _left: str, _right: str) -> float:
        return self.score

    def has_pending_segment_review_match(self, **_kwargs) -> bool:
        return False

    def create_duplicate_match(self, **kwargs) -> None:
        self.created.append(kwargs)


def _incident(*, raw_message_id: int, village_id: int, condition_id: int):
    return SimpleNamespace(
        id=uuid4(),
        raw_message_id=raw_message_id,
        village_id=village_id,
        condition_id=condition_id,
        duplicate_flag=False,
        duplicate_level=None,
        duplicate_similarity_score=None,
        verification_status="auto_processed",
        verification_reason=None,
    )


@pytest.mark.parametrize(
    (
        "new_raw_message_id",
        "canonical_raw_message_id",
        "village_id",
        "condition_id",
        "new_segment",
        "canonical_segment",
        "score",
    ),
    [
        (
            10464,
            11553,
            1519,
            5,
            "إطلاق قذائف هاون باتجاه بلدة زوطر الشرقية",
            "أقدم العدو فجراً على إطلاق قذائف هاون باتجاه بلدة زوطر الشرقية",
            1.0,
        ),
        (
            11556,
            11553,
            813,
            5,
            "قذيفة هاون إسرائيلية استهدفت أحد المنازل في حلتا",
            "استهدفت قذيفة هاون محيط المنازل في بلدة حلتا",
            0.60,
        ),
    ],
)
def test_recon_pairs_queue_segment_review_without_auto_merge(
    new_raw_message_id: int,
    canonical_raw_message_id: int,
    village_id: int,
    condition_id: int,
    new_segment: str,
    canonical_segment: str,
    score: float,
) -> None:
    canonical = _incident(
        raw_message_id=canonical_raw_message_id,
        village_id=village_id,
        condition_id=condition_id,
    )
    source = SegmentReviewSource(
        incident=canonical,
        extraction_result={
            "sub_events": [
                {
                    "locations": [{"village": "fixture"}],
                    "evidence_span": canonical_segment,
                }
            ]
        },
        match_result={
            "village_matches": [
                {
                    "event_index": 0,
                    "matched_village_id": village_id,
                    "matched_condition_id": condition_id,
                }
            ]
        },
    )
    repository = _IncidentRepositoryStub(source, score)
    new_incident = _incident(
        raw_message_id=new_raw_message_id,
        village_id=village_id,
        condition_id=condition_id,
    )

    queued = SegmentReviewDedupService(
        repository,  # type: ignore[arg-type]
        similarity_threshold=0.60,
        window_days=7,
        max_candidates=20,
    ).queue_for_incident(
        incident=new_incident,
        raw_message_id=new_raw_message_id,
        source_id=3,
        event_datetime=datetime(2026, 9, 16, tzinfo=timezone.utc),
        segment_text=new_segment,
    )

    assert queued == 1
    assert len(repository.created) == 1
    assert repository.created[0]["status"] == MatchStatus.pending
    assert repository.created[0]["similarity_score"] == score
    assert new_incident.duplicate_flag is True
    assert new_incident.duplicate_level == "segment"
    assert new_incident.verification_status == "needs_verification"
    assert canonical.duplicate_flag is False
    assert repository.db.commit_calls == 1
