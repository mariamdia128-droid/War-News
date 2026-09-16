from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.llm.dtos import (
    CasualtyScope,
    ExtractionCasualties,
    ExtractionResult,
    ExtractionSubEvent,
    VillageRoleEntry,
)
from app.news.dtos import MatchResultStatus
from app.news.models import Incident, IncidentDetail
from app.news.services.dedup.fast_path_dedup import FastPathDedupOutcome
from app.news.services.matching.matching_service import MatchingService
from app.news.services.materialization.incident_materialization_service import (
    IncidentMaterializationService,
)
from tests.test_incident_materialization_service import (
    _SessionStub,
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
                locations=[VillageRoleEntry(village="كفر رمان", deaths=8, injuries=11)],
                action_text="غارة على منزل",
                casualties=ExtractionCasualties(
                    deaths=8,
                    injuries=11,
                    total_deaths=8,
                    total_injuries=11,
                ),
                evidence_span=HOUSE_SPAN,
            ),
            ExtractionSubEvent(
                locations=[VillageRoleEntry(village="كفر رمان", deaths=1, injuries=2)],
                action_text="استهداف سيارة",
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


class _RouteVillageRepositoryStub:
    def find_similar(self, text: str, limit: int = 5):
        village_id = 652 if "حاروف" in text else 1529
        return [
            (
                SimpleNamespace(
                    id=village_id,
                    ref_name_ar=text,
                    caza_ar="النبطية",
                    caza_en="Nabatiyeh",
                    coord_x=None,
                    coord_y=None,
                ),
                1.0,
            )
        ]


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


def test_message_10395_creates_only_declared_location_action_pairs() -> None:
    db = _SessionStub()
    service = IncidentMaterializationService(db)  # type: ignore[arg-type]
    extraction = _two_action_extraction()
    match_result = MatchingService(
        _SimilarRepositoryStub(851, 0.9),
        _ConditionByTextStub(),
    ).match(extraction)
    representative = _representative(
        match_result=match_result.model_dump(mode="json")
    )
    representative.extraction_result = extraction.model_dump(mode="json")
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


def test_raw_9302_route_scoped_casualty_is_not_copied_to_both_endpoints() -> None:
    route_span = "شهيد في غارة استهدفت دراجة على طريق مرج حاروف - زبدين"
    extraction = ExtractionResult(
        is_relevant=True,
        village=["حاروف", "زبدين"],
        village_roles=[],
        action_description="غارة على دراجة نارية",
        sub_events=[
            ExtractionSubEvent(
                locations=[
                    VillageRoleEntry(village="حاروف"),
                    VillageRoleEntry(
                        village="زبدين",
                        deaths=1,
                        evidence_span=route_span,
                    ),
                ],
                action_text="غارة على دراجة نارية",
                casualties=ExtractionCasualties(
                    deaths=1,
                    total_deaths=1,
                    male_deaths=1,
                ),
                evidence_span=route_span,
            )
        ],
        casualty_scope=CasualtyScope.per_village_exact,
        casualties=ExtractionCasualties(),
        model="test",
        extracted_at=datetime.now(timezone.utc),
    )
    match_result = MatchingService(
        _RouteVillageRepositoryStub(),
        _ConditionByTextStub(),
    ).match(extraction)
    representative = _representative(
        match_result=match_result.model_dump(mode="json")
    )
    representative.raw_text = route_span
    representative.extraction_result = extraction.model_dump(mode="json")
    db = _SessionStub()

    created = IncidentMaterializationService(db).process_fast_path(  # type: ignore[arg-type]
        representative,
        SimpleNamespace(
            decide_for_village=lambda **_kwargs: SimpleNamespace(
                outcome=FastPathDedupOutcome.materialize,
                representative_raw_message_id=None,
                canonical_incident_id=None,
            )
        ),
    )

    assert len(created) == 2
    assert sorted(incident.deaths or 0 for incident in created) == [0, 1]
    assert created[0].story_group_id == created[1].story_group_id
    assert created[0].story_group_id is not None
