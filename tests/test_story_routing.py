from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.llm.dtos import StoryRelationship, StoryRelationshipClassification
from app.news.models import Incident, IncidentDetail, IncidentUpdate, UpdateAction
from app.news.repositories.incident_repository import IncidentRepository
from app.news.services.dedup.fast_path_dedup import FastPathDedupOutcome
from app.news.services.dedup.story_continuation_router import StoryRoute
from app.news.services.materialization.incident_materialization_service import (
    IncidentMaterializationService,
)
from tests.test_incident_materialization_service import (
    _SessionStub,
    _match_result,
    _representative,
)
from tests.test_story_revision_backstop import (
    DRONE_CAR,
    FULL_HOUSE,
    MOH_CAR,
    PRELIMINARY_CAR,
    SPARSE_CASUALTIES,
    ZAHRAA,
)


def _incident(**overrides) -> SimpleNamespace:
    values = dict(
        id=uuid4(),
        village_id=851,
        condition_id=1,
        raw_message_id=100,
        deaths=8,
        injuries=12,
        total_deaths=8,
        total_injuries=12,
        martyrs=None,
        note=None,
        details_pending=False,
        story_group_id=None,
        khabar=FULL_HOUSE,
        duplicate_flag=False,
        verification_status="auto_processed",
        verification_reason=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_apply_story_revision_updates_supplied_fields_only() -> None:
    existing = Incident()
    existing.id = uuid4()
    existing.deaths = 2
    existing.injuries = 2
    existing.total_deaths = 2
    existing.total_injuries = 2
    existing.martyrs = None
    existing.details_pending = False
    detail = IncidentDetail(incident_id=existing.id, male_d=None)
    db = MagicMock()
    db.get.return_value = SimpleNamespace(source_name="NNA", origin_account=None, source_platform=None)
    db.scalar.side_effect = [None, detail]
    repo = IncidentRepository(db)

    repo.apply_story_revision(
        existing,
        {
            "deaths": 8,
            "injuries": 11,
            "total_deaths": 8,
            "total_injuries": 11,
            "khabar": FULL_HOUSE,
        },
        raw_message_id=5311,
    )

    assert existing.deaths == 8
    assert existing.injuries == 11
    update = next(value for value in db.add.call_args_list if isinstance(value.args[0], IncidentUpdate)).args[0]
    assert update.action == UpdateAction.pipeline_merge
    assert update.performed_by is None
    assert update.new_values["story_revision"] is True
    assert update.new_values["merged_from"]["raw_message_id"] == 5311


def test_apply_story_revision_does_not_blank_unmentioned_fields() -> None:
    existing = Incident()
    existing.id = uuid4()
    existing.deaths = 8
    existing.injuries = 12
    existing.total_deaths = 8
    existing.total_injuries = 12
    existing.martyrs = None
    existing.details_pending = False
    db = MagicMock()
    db.get.return_value = None
    db.scalar.side_effect = [None, None]
    repo = IncidentRepository(db)

    repo.apply_story_revision(
        existing,
        {"khabar": ZAHRAA, "martyrs": "زهراء أيوب"},
        raw_message_id=5310,
    )

    assert existing.deaths == 8
    assert existing.injuries == 12
    assert existing.martyrs == "زهراء أيوب"


def test_apply_story_revision_is_idempotent_for_same_message() -> None:
    existing = Incident()
    existing.id = uuid4()
    existing.deaths = 8
    existing.injuries = 12
    existing.total_deaths = 8
    existing.total_injuries = 12
    existing.details_pending = False
    db = MagicMock()
    db.scalar.return_value = 99
    repo = IncidentRepository(db)

    repo.apply_story_revision(
        existing,
        {"deaths": 11, "injuries": 16, "total_deaths": 11, "total_injuries": 16},
        raw_message_id=4423,
    )

    assert existing.deaths == 8
    assert existing.injuries == 12
    db.add.assert_not_called()


def _fast_dedup_materialize():
    return SimpleNamespace(
        decide_for_village=lambda **_kwargs: SimpleNamespace(
            outcome=FastPathDedupOutcome.materialize,
            representative_raw_message_id=None,
            canonical_incident_id=None,
            canonical_incident=None,
            matched_incident=None,
            similarity_score=None,
            similarity_method=None,
        ),
        incidents=MagicMock(),
    )


def test_revision_route_updates_existing_and_does_not_create() -> None:
    db = _SessionStub()
    canonical = _incident(deaths=2, injuries=2, total_deaths=2, total_injuries=2)
    router = SimpleNamespace(
        incidents=MagicMock(),
        route_for_village=lambda **_kwargs: StoryRoute(
            relationship=StoryRelationship.revision,
            candidate=canonical,  # type: ignore[arg-type]
            classification=StoryRelationshipClassification(
                relationship=StoryRelationship.revision,
                relationship_evidence="المعلومات الأولية",
                candidate_incident_id=canonical.id,
            ),
        ),
    )
    service = IncidentMaterializationService(db, story_router=router)  # type: ignore[arg-type]
    representative = _representative(match_result=_match_result(village_id=851, condition_id=1))
    representative.raw_text = PRELIMINARY_CAR
    representative.id = 4339

    created = service.process_fast_path(representative, _fast_dedup_materialize())  # type: ignore[arg-type]

    assert created == []
    router.incidents.apply_story_revision.assert_called_once()
    assert not any(isinstance(value, Incident) for value in db.committed)


def test_duplicate_route_merges_and_does_not_create() -> None:
    db = _SessionStub()
    canonical = _incident(condition_id=1, khabar=MOH_CAR, deaths=1, injuries=2)
    router = SimpleNamespace(
        incidents=MagicMock(),
        route_for_village=lambda **_kwargs: StoryRoute(
            relationship=StoryRelationship.duplicate,
            candidate=canonical,  # type: ignore[arg-type]
            classification=StoryRelationshipClassification(
                relationship=StoryRelationship.duplicate,
                relationship_evidence="same car action",
                candidate_incident_id=canonical.id,
            ),
        ),
    )
    router.incidents.merge_existing = MagicMock()
    service = IncidentMaterializationService(db, story_router=router)  # type: ignore[arg-type]
    representative = _representative(match_result=_match_result(village_id=851, condition_id=3))
    representative.raw_text = DRONE_CAR
    representative.id = 4389
    fast_dedup = _fast_dedup_materialize()

    created = service.process_fast_path(representative, fast_dedup)  # type: ignore[arg-type]

    assert created == []
    fast_dedup.incidents.merge_existing.assert_called_once()
    assert not any(isinstance(value, Incident) for value in db.committed)


def test_distinct_sub_event_creates_and_links() -> None:
    db = _SessionStub()
    house = _incident(khabar=FULL_HOUSE)
    router = SimpleNamespace(
        incidents=MagicMock(),
        route_for_village=lambda **_kwargs: StoryRoute(
            relationship=StoryRelationship.distinct_sub_event,
            candidate=house,  # type: ignore[arg-type]
            classification=StoryRelationshipClassification(
                relationship=StoryRelationship.distinct_sub_event,
                relationship_evidence="car vs house",
                candidate_incident_id=house.id,
            ),
        ),
    )
    service = IncidentMaterializationService(db, story_router=router)  # type: ignore[arg-type]
    representative = _representative(match_result=_match_result(village_id=851, condition_id=3))
    representative.raw_text = DRONE_CAR

    created = service.process_fast_path(representative, _fast_dedup_materialize())  # type: ignore[arg-type]

    assert len(created) == 1
    router.incidents.link_story_group.assert_called_once()
    assert created[0].village_id == 851
    assert created[0].condition_id == 3


def test_unrelated_creates_new_incident() -> None:
    db = _SessionStub()
    router = SimpleNamespace(
        incidents=MagicMock(),
        route_for_village=lambda **_kwargs: None,
    )
    service = IncidentMaterializationService(db, story_router=router)  # type: ignore[arg-type]
    representative = _representative()

    created = service.process_fast_path(representative, _fast_dedup_materialize())  # type: ignore[arg-type]

    assert len(created) == 1
    router.incidents.apply_story_revision.assert_not_called()
    router.incidents.link_story_group.assert_not_called()


def test_kfar_sparse_and_named_victim_revision_chain() -> None:
    """#10/#11 and Zahraa route as revisions of the fuller house/car report."""
    db = _SessionStub()
    canonical = _incident()
    texts = (SPARSE_CASUALTIES, PRELIMINARY_CAR, ZAHRAA)
    for text in texts:
        router = SimpleNamespace(
            incidents=MagicMock(),
            route_for_village=lambda **_kwargs: StoryRoute(
                relationship=StoryRelationship.revision,
                candidate=canonical,  # type: ignore[arg-type]
                classification=StoryRelationshipClassification(
                    relationship=StoryRelationship.revision,
                    candidate_incident_id=canonical.id,
                ),
            ),
        )
        service = IncidentMaterializationService(db, story_router=router)  # type: ignore[arg-type]
        representative = _representative(match_result=_match_result(village_id=851))
        representative.raw_text = text
        created = service.process_fast_path(representative, _fast_dedup_materialize())  # type: ignore[arg-type]
        assert created == []
        router.incidents.apply_story_revision.assert_called_once()
