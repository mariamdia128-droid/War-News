from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.llm.dtos import StoryRelationship
from app.news.services.dedup.story_relationship_service import (
    StoryRelationshipService,
)
from app.news.services.incident_details.story_revision_backstop import (
    detect_story_revision_backstop,
)


PRELIMINARY_CAR = (
    "غارة من الطيران المسير استهدفت سيارة في بلدة كفررمان "
    "والمعلومات الأولية تشير إلى وقوع إصابتين"
)
SPARSE_CASUALTIES = "وقوع إصابات في غارة كفررمان"
MOH_CAR = (
    "عاجل | وزارة الصحة: استشهاد مسعف في كشافة الرسالة وإصابة 2 آخرين "
    "في غارة العدو على سيارة في كفررمان"
)
FULL_HOUSE = (
    "غارة العدو الإسرائيلي على منزل في بلدة كفررمان أدت إلى 8 شهداء "
    "من بينهم طفل وسيدتان و11 جريحا من بينهم 4 أطفال وسيدتان واستشهاد مسعف"
)
ZAHRAA = (
    "بلدية كفررمان تنعى الموظفة في البلدية زهراء أيوب، التي ارتقت شهيدة "
    "مع أفراد عائلتها إثر الغارة الإسرائيلية التي استهدفت منزلهم ليلاً في البلدة"
)
DRONE_CAR = (
    "استهدفت مسيّرة إسرائيلية سيارة مدنية في بلدة كفررمان كان بداخلها "
    "3 مسعفين ما أدى إلى استشهاد مسعف وإصابة اثنين آخرين"
)


def test_backstop_classifies_preliminary_toll_as_revision() -> None:
    result = detect_story_revision_backstop(PRELIMINARY_CAR)
    assert result.plausible is True
    assert result.relationship_hint == "revision"
    assert "المعلومات الأولية" in result.matched_keywords


def test_backstop_classifies_named_victim_follow_up_as_revision() -> None:
    result = detect_story_revision_backstop(
        ZAHRAA,
        candidate_text=FULL_HOUSE,
        candidate_deaths=8,
        candidate_injuries=12,
    )
    assert result.plausible is True
    assert result.relationship_hint == "revision"
    assert "تنعى" in result.matched_keywords


def test_backstop_named_victim_without_numeric_candidate_is_not_revision() -> None:
    result = detect_story_revision_backstop(
        ZAHRAA,
        candidate_text="غارة على بلدة كفررمان",
        candidate_deaths=None,
        candidate_injuries=None,
    )
    assert result.plausible is False


def test_classifier_downgrades_revision_without_candidate() -> None:
    service = StoryRelationshipService()
    result = service.classify(
        current_text=PRELIMINARY_CAR,
        candidate_text=None,
        candidate_incident_id=None,
        claimed_relationship=StoryRelationship.revision,
        claimed_evidence="حصيلة أولية",
    )
    assert result.relationship == StoryRelationship.unrelated
    assert result.needs_review is True
    assert result.review_reason is not None
    assert "no candidate" in result.review_reason


def test_classifier_downgrades_backstop_revision_without_any_candidates() -> None:
    service = StoryRelationshipService()
    result = service.classify_best(
        current_text=PRELIMINARY_CAR,
        candidates=[],
    )
    assert result.relationship == StoryRelationship.unrelated
    assert result.needs_review is True


def test_zahraa_is_revision_of_numeric_house_toll() -> None:
    service = StoryRelationshipService()
    candidate_id = uuid4()
    result = service.classify(
        current_text=ZAHRAA,
        candidate_text=FULL_HOUSE,
        candidate_incident_id=candidate_id,
        candidate_deaths=8,
        candidate_injuries=12,
        embedding_similarity=0.58,
    )
    assert result.relationship == StoryRelationship.revision
    assert result.candidate_incident_id == candidate_id


def test_car_drone_is_duplicate_of_moh_car_strike() -> None:
    service = StoryRelationshipService()
    candidate_id = uuid4()
    result = service.classify(
        current_text=DRONE_CAR,
        candidate_text=MOH_CAR,
        candidate_incident_id=candidate_id,
        embedding_similarity=0.66,
    )
    assert result.relationship == StoryRelationship.duplicate


def test_car_vs_house_is_distinct_sub_event() -> None:
    service = StoryRelationshipService()
    house_only = "غارة على منزل في كفررمان أدت إلى 8 شهداء بينهم طفل وسيدتان"
    result = service.classify(
        current_text=DRONE_CAR,
        candidate_text=house_only,
        candidate_incident_id=uuid4(),
        embedding_similarity=0.60,
    )
    assert result.relationship == StoryRelationship.distinct_sub_event


def test_sparse_early_report_is_revision_of_fuller_toll() -> None:
    service = StoryRelationshipService()
    result = service.classify(
        current_text=SPARSE_CASUALTIES,
        candidate_text=FULL_HOUSE,
        candidate_incident_id=uuid4(),
        candidate_deaths=8,
        embedding_similarity=0.52,
    )
    assert result.relationship == StoryRelationship.revision


def test_classify_best_prefers_car_duplicate_over_mixed_bulletin() -> None:
    service = StoryRelationshipService()
    car_id = uuid4()
    mixed_id = uuid4()
    candidates = [
        SimpleNamespace(
            incident=SimpleNamespace(
                id=mixed_id,
                khabar=FULL_HOUSE,
                deaths=8,
                injuries=12,
                total_deaths=8,
                total_injuries=12,
            ),
            embedding_similarity=0.74,
        ),
        SimpleNamespace(
            incident=SimpleNamespace(
                id=car_id,
                khabar=MOH_CAR,
                deaths=1,
                injuries=2,
                total_deaths=1,
                total_injuries=2,
            ),
            embedding_similarity=0.66,
        ),
    ]
    result = service.classify_best(current_text=DRONE_CAR, candidates=candidates)
    assert result.relationship == StoryRelationship.duplicate
    assert result.candidate_incident_id == car_id
