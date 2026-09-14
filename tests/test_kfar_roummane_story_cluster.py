from datetime import datetime, timezone
from uuid import uuid4

from app.news.dtos import RelatedIncidentDTO, TollRevisionDTO
from app.news.services.dedup.story_relationship_service import StoryRelationshipService
from app.llm.dtos import StoryRelationship
from app.news.services.incident_details.casualty_gender_evidence import (
    apply_gendered_occupation_casualty_evidence,
)
from app.llm.dtos import ExtractionCasualties
from tests.test_story_revision_backstop import (
    DRONE_CAR,
    FULL_HOUSE,
    MOH_CAR,
    PRELIMINARY_CAR,
    SPARSE_CASUALTIES,
    ZAHRAA,
)
from types import SimpleNamespace


def _candidate(text: str, *, deaths: int | None, injuries: int | None, embedding: float):
    return SimpleNamespace(
        incident=SimpleNamespace(
            id=uuid4(),
            khabar=text,
            deaths=deaths,
            injuries=injuries,
            total_deaths=deaths,
            total_injuries=injuries,
        ),
        embedding_similarity=embedding,
    )


def test_kfar_cluster_classifications_are_coherent() -> None:
    """Acceptance: the §0 cluster resolves as revision / duplicate, not new events."""
    service = StoryRelationshipService()
    house = _candidate(FULL_HOUSE, deaths=8, injuries=12, embedding=0.58)
    car = _candidate(MOH_CAR, deaths=1, injuries=2, embedding=0.66)

    sparse = service.classify_best(current_text=SPARSE_CASUALTIES, candidates=[house])
    prelim = service.classify_best(current_text=PRELIMINARY_CAR, candidates=[house, car])
    zahraa = service.classify_best(current_text=ZAHRAA, candidates=[house])
    drone = service.classify_best(current_text=DRONE_CAR, candidates=[house, car])

    assert sparse.relationship == StoryRelationship.revision
    assert prelim.relationship == StoryRelationship.revision
    assert zahraa.relationship == StoryRelationship.revision
    assert drone.relationship == StoryRelationship.duplicate
    assert drone.candidate_incident_id == car.incident.id


def test_full_house_report_sets_paramedic_male_death() -> None:
    result = apply_gendered_occupation_casualty_evidence(
        FULL_HOUSE,
        ExtractionCasualties(deaths=8, injuries=12),
    )
    assert result.male_deaths == 1
    assert result.deaths == 8


def test_toll_revision_and_related_dtos_default_for_detail_payload() -> None:
    revision = TollRevisionDTO(
        updated_at=datetime(2026, 9, 7, 9, 21, tzinfo=timezone.utc),
        old_deaths=8,
        old_injuries=12,
        new_deaths=11,
        new_injuries=16,
    )
    related = RelatedIncidentDTO(
        id=uuid4(),
        village="Kfar Roummane",
        condition="Drone Failure",
        relation="same_location_sub_event",
        total_deaths=1,
        total_injuries=2,
    )
    assert revision.old_deaths == 8
    assert related.relation == "same_location_sub_event"
