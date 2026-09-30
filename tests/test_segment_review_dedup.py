import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.news.models import MatchStatus
from app.news.repositories.incident_repository import SegmentReviewSource
from app.news.services.dedup.segment_review_dedup import SegmentReviewDedupService

CASES = json.loads((Path(__file__).parent / "fixtures" / "segment_review_cases.json").read_text(encoding="utf-8"))


class _DbStub:
    def __init__(self) -> None: self.commit_calls = 0
    def commit(self) -> None: self.commit_calls += 1


class _RepositoryStub:
    def __init__(self, source: SegmentReviewSource, score: float = 0.90) -> None:
        self.source, self.score, self.db = source, score, _DbStub()
        self.created: list[dict] = []
        self.query: dict | None = None
    def find_segment_review_sources(self, **kwargs):
        self.query = kwargs
        return [self.source]
    def segment_text_similarity(self, _left: str, _right: str) -> float: return self.score
    def has_pending_segment_review_match(self, **_kwargs) -> bool: return False
    def create_duplicate_match(self, **kwargs) -> None: self.created.append(kwargs)


def _incident(raw_id: int, event_dt: datetime):
    return SimpleNamespace(
        id=uuid4(), raw_message_id=raw_id, village_id=976, condition_id=5,
        event_date=event_dt.date(), event_time=event_dt.time().replace(tzinfo=None),
        duplicate_flag=False, duplicate_level=None, duplicate_similarity_score=None,
        verification_status="auto_processed", verification_reason=None,
    )


def _source(raw_id: int, event_dt: datetime, segment: str, *, raw_text: str | None = None,
            village_ids: tuple[int, ...] = (976,), extra_events: int = 0) -> SegmentReviewSource:
    events = [{"locations": [{"village": "المنصوري", "role": "target"}],
               "action_text": "قصف مدفعي استهدف البلدة", "evidence_span": segment}]
    events += [{"locations": [{"village": f"fixture-{i}", "role": "target"}],
                "action_text": "قصف مدفعي استهدف بلدة أخرى",
                "evidence_span": "قصف مدفعي استهدف بلدة أخرى مساء اليوم"} for i in range(extra_events)]
    matches = [{"event_index": min(i, len(events) - 1), "matched_village_id": village_id,
                "matched_condition_id": 5, "village_role": "target"}
               for i, village_id in enumerate(village_ids)]
    return SegmentReviewSource(
        incident=_incident(raw_id, event_dt), extraction_result={"sub_events": events},
        match_result={"village_matches": matches}, raw_text=raw_text or segment,
        message_datetime=event_dt,
    )


def _queue(source: SegmentReviewSource, current_dt: datetime, current_text: str,
           *, current_raw_id: int = 500, score: float = 0.90):
    repository = _RepositoryStub(source, score)
    current = _incident(current_raw_id, current_dt)
    queued = SegmentReviewDedupService(repository).queue_for_incident(  # type: ignore[arg-type]
        incident=current, raw_message_id=current_raw_id, source_id=3,
        event_datetime=current_dt, segment_text=current_text,
    )
    return queued, repository, current


def test_positive_cross_source_full_clauses_are_queued() -> None:
    now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
    source = _source(400, now - timedelta(minutes=45),
                     "قصف مدفعي إسرائيلي استهدف أطراف بلدة المنصوري مساء اليوم قرب المنازل")
    queued, repository, current = _queue(
        source, now, "قصف مدفعي معاد استهدف أطراف بلدة المنصوري مساء اليوم قرب المنازل")
    assert queued == 1
    assert repository.created[0]["status"] == MatchStatus.pending
    assert current.duplicate_flag and current.duplicate_level == "segment"


@pytest.mark.parametrize("gap, expected", [(timedelta(hours=24), 1), (timedelta(hours=24, minutes=1), 0)])
def test_event_gap_boundary(gap: timedelta, expected: int) -> None:
    now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
    text = "قصف مدفعي استهدف أطراف بلدة المنصوري مساء يوم الجمعة"
    queued, _, _ = _queue(_source(400, now - gap, text), now, text)
    assert queued == expected


def test_newer_case_b_candidate_is_rejected_at_score_one() -> None:
    case = CASES["case_b"]
    current = datetime(2026, 9, 25, 7, 35, tzinfo=timezone.utc)
    source = _source(case["candidate_raw_id"], datetime(2026, 9, 28, 9, 8, tzinfo=timezone.utc),
                     "قصف مدفعي استهدف وادي الحجير خلال ساعات الليل")
    queued, _, _ = _queue(source, current, case["current_text"],
                          current_raw_id=case["current_raw_id"], score=1.0)
    assert queued == 0


def test_case_a_is_rejected_by_time_gate() -> None:
    case = CASES["case_a"]
    source = _source(case["candidate_raw_id"], datetime(2026, 9, 23, 10, 37, tzinfo=timezone.utc),
                     case["candidate_segment"], raw_text=case["candidate_text"])
    queued, _, _ = _queue(source, datetime(2026, 9, 25, 16, 58, tzinfo=timezone.utc),
                          case["current_text"], current_raw_id=case["current_raw_id"], score=0.6111111)
    assert queued == 0


def test_roundup_cannot_be_main() -> None:
    now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
    source = _source(400, now - timedelta(hours=1),
                     "قصف مدفعي استهدف وادي الحجير خلال ساعات الليل",
                     raw_text=CASES["case_b"]["candidate_text"],
                     village_ids=(976, 1186, 1464), extra_events=2)
    queued, _, _ = _queue(source, now, "قصف مدفعي استهدف وادي الحجير خلال ساعات الليل")
    assert queued == 0


def test_two_sub_events_in_one_village_are_not_a_roundup() -> None:
    now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
    source = _source(
        400, now - timedelta(hours=1),
        "قصف مدفعي استهدف بلدة المنصوري قرب المنازل مساء اليوم",
        raw_text="قصف دبابة بلدة المنصوري بالتزامن مع تمشيط بالرشاشات",
        village_ids=(976,), extra_events=1,
    )
    # The fixture's second action uses another display string, but both matches
    # resolve to the same canonical village id; canonical place identity wins.
    source.extraction_result["sub_events"][1]["locations"][0]["village"] = "المنصوري"
    assert not SegmentReviewDedupService._is_roundup_source(source)


def test_three_distinct_target_villages_are_a_roundup_without_marker() -> None:
    now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
    source = _source(
        400, now - timedelta(hours=1),
        "قصف مدفعي استهدف بلدة المنصوري قرب المنازل مساء اليوم",
        raw_text="قصف متفرق على قرى جنوبية",
        village_ids=(976, 1186, 1464), extra_events=2,
    )
    assert SegmentReviewDedupService._is_roundup_source(source)


def test_single_village_summary_marker_is_a_roundup() -> None:
    now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
    source = _source(
        400, now - timedelta(hours=1),
        "قصف مدفعي استهدف بلدة المنصوري قرب المنازل مساء اليوم",
        raw_text="ملخص الاعتداءات على بلدة المنصوري حتى الساعة التاسعة",
    )
    assert SegmentReviewDedupService._is_roundup_source(source)


@pytest.mark.parametrize("segment", ["قصف", "وادي الحجير"])
def test_bare_segment_is_rejected(segment: str) -> None:
    service = SegmentReviewDedupService(SimpleNamespace())  # type: ignore[arg-type]
    assert not service._is_informative_segment(segment)


@pytest.mark.parametrize(
    "text",
    [
        "غارات إسرائيلية تستهدف النبطية الفوقا",
        "تحرك للدبابات الإسرائيلية شرق الخيام وإطلاق نار كثيف في المنطقة",
    ],
)
def test_terse_admin_confirmed_reports_remain_informative(text: str) -> None:
    service = SegmentReviewDedupService(SimpleNamespace())  # type: ignore[arg-type]
    assert service._is_informative_segment(text)


def test_case_c_modifier_conflict_and_missing_modifier_control() -> None:
    service = SegmentReviewDedupService(SimpleNamespace())  # type: ignore[arg-type]
    assert service._has_modifier_conflict(CASES["case_c"]["current_text"], CASES["case_c"]["candidate_text"])
    assert not service._has_modifier_conflict("قصف مدفعي استهدف البلدة مساء اليوم",
                                              "قصف مدفعي معاد استهدف البلدة مساء اليوم")


def test_case_c_bare_extracted_span_cannot_queue_without_roundup_gate() -> None:
    case = CASES["case_c"]
    now = datetime(2026, 9, 27, 15, 43, tzinfo=timezone.utc)
    source = _source(case["candidate_raw_id"], now - timedelta(hours=4, minutes=14), "قصف")
    queued, _, _ = _queue(source, now, case["current_text"],
                          current_raw_id=case["current_raw_id"], score=1.0)
    assert queued == 0


def test_explicit_secondary_target_conflict_blocks_but_missing_target_does_not() -> None:
    service = SegmentReviewDedupService(SimpleNamespace())  # type: ignore[arg-type]
    assert service._has_named_target_conflict(
        "قصف مدفعي استهدف عيتا الجبل وبيت ياحون مساء اليوم",
        "قصف مدفعي استهدف عيتا الجبل وبرعشيت مساء اليوم",
    )
    assert not service._has_named_target_conflict(
        "قصف مدفعي استهدف عيتا الجبل مساء اليوم",
        "قصف مدفعي استهدف عيتا الجبل وبيت ياحون مساء اليوم",
    )


def test_balanced_similarity_uses_weaker_direction() -> None:
    class _ScalarDb:
        statement = None
        def scalar(self, statement):
            self.statement = statement
            return 0.25

    db = _ScalarDb()
    score = __import__(
        "app.news.repositories.incident_repository", fromlist=["IncidentRepository"]
    ).IncidentRepository(db).segment_text_similarity("قصف", "قصف مدفعي استهدف البلدة")
    assert score == 0.25
    assert "least" in str(db.statement).lower()


def test_query_receives_named_time_gate() -> None:
    now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
    text = "قصف مدفعي استهدف أطراف بلدة المنصوري مساء اليوم"
    _, repository, _ = _queue(_source(400, now - timedelta(minutes=30), text), now, text)
    assert repository.query["event_datetime"] == now
    assert repository.query["max_event_gap_hours"] == 24
