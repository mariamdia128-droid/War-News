from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.llm.dtos import ExtractionCasualties, ExtractionResult, ExtractionSubEvent
from app.news.dtos import MatchResultStatus
from app.news.models import Incident, IncidentDetail
from app.news.services.dedup.fast_path_dedup import FastPathDedupOutcome
from app.news.services.matching.matching_service import MatchingService
from app.news.services.materialization.incident_materialization_service import (
    IncidentMaterializationService,
)
from tests.test_incident_materialization_service import (
    _SessionStub,
    _match_result,
    _representative,
)
from tests.test_matching_service import _SimilarRepositoryStub, _extraction


HOUSE_SPAN = "غارة على منزل في كفررمان أدت إلى 8 شهداء و11 جريحاً"
CAR_SPAN = "استُهدفت سيارة فاستُشهد مسعف وأصيب 2"


def _two_action_extraction() -> ExtractionResult:
    return ExtractionResult(
        is_relevant=True,
        village=["كفر رمان"],
        action_description="غارات على منزل وسيارة",
        sub_events=[
            ExtractionSubEvent(
                action_description="غارة على منزل",
                casualties=ExtractionCasualties(
                    deaths=8,
                    injuries=11,
                    total_deaths=8,
                    total_injuries=11,
                ),
                evidence_span=HOUSE_SPAN,
            ),
            ExtractionSubEvent(
                action_description="استهداف سيارة",
                casualties=ExtractionCasualties(
                    deaths=1,
                    injuries=2,
                    total_deaths=1,
                    total_injuries=2,
                    male_deaths=1,
                ),
                evidence_span=CAR_SPAN,
            ),
        ],
        casualties=ExtractionCasualties(),
        model="test",
        extracted_at=datetime.now(timezone.utc),
    )


class _ConditionByTextStub:
    def find_similar(self, text: str, limit: int = 5):
        if "سيار" in text:
            return [(SimpleNamespace(id=8), 0.91)]
        return [(SimpleNamespace(id=1), 0.93)]


def test_matching_scores_each_sub_event_action() -> None:
    service = MatchingService(
        _SimilarRepositoryStub(851, 0.9),
        _ConditionByTextStub(),
    )

    result = service.match(_two_action_extraction())

    assert len(result.sub_event_matches) == 2
    assert result.sub_event_matches[0].matched_condition_id == 1
    assert result.sub_event_matches[1].matched_condition_id == 8
    assert result.sub_event_matches[0].condition_match_status == MatchResultStatus.matched
    assert result.sub_event_matches[1].condition_match_status == MatchResultStatus.matched


def test_fast_path_creates_one_incident_per_sub_event() -> None:
    db = _SessionStub()
    service = IncidentMaterializationService(db)  # type: ignore[arg-type]
    representative = _representative(
        match_result={
            **_match_result(village_id=851, condition_id=1),
            "sub_event_matches": [
                {
                    "index": 0,
                    "action_description": "غارة على منزل",
                    "evidence_span": HOUSE_SPAN,
                    "matched_condition_id": 1,
                    "condition_confidence": 0.93,
                    "condition_match_status": "matched",
                    "condition_review_required": False,
                },
                {
                    "index": 1,
                    "action_description": "استهداف سيارة",
                    "evidence_span": CAR_SPAN,
                    "matched_condition_id": 8,
                    "condition_confidence": 0.91,
                    "condition_match_status": "matched",
                    "condition_review_required": False,
                },
            ],
        }
    )
    representative.extraction_result = _two_action_extraction().model_dump(mode="json")
    fast_dedup = SimpleNamespace(
        decide_for_village=lambda **_kwargs: SimpleNamespace(
            outcome=FastPathDedupOutcome.materialize,
            representative_raw_message_id=None,
            canonical_incident_id=None,
        )
    )

    created = service.process_fast_path(representative, fast_dedup)  # type: ignore[arg-type]

    incidents = [value for value in db.committed if isinstance(value, Incident)]
    details = [value for value in db.committed if isinstance(value, IncidentDetail)]
    assert len(created) == 2
    assert len(incidents) == 2
    counts = sorted(
        (incident.deaths, incident.injuries, incident.condition_id)
        for incident in incidents
    )
    assert counts == [(1, 2, 8), (8, 11, 1)]
    assert incidents[0].exact_hash != incidents[1].exact_hash
    assert incidents[0].story_group_id is not None
    assert incidents[0].story_group_id == incidents[1].story_group_id
    assert {incident.village_id for incident in incidents} == {851}
    male_deaths = {detail.male_d for detail in details}
    assert male_deaths == {1, None}


def test_single_action_extraction_does_not_split() -> None:
    result = MatchingService(
        _SimilarRepositoryStub(11, 0.7),
        _SimilarRepositoryStub(5, 0.8),
    ).match(_extraction())

    assert result.sub_event_matches == []
    assert result.matched_condition_id == 5
