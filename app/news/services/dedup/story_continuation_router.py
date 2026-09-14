from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.llm.dtos import StoryRelationship, StoryRelationshipClassification
from app.news.models import Incident
from app.news.repositories.incident_repository import IncidentRepository, StoryCandidate
from app.news.services.clustering.raw_message_embedding_service import strip_boilerplate
from app.news.services.dedup.story_candidate_search import StoryCandidateSearch
from app.news.services.dedup.story_relationship_service import StoryRelationshipService


@dataclass(frozen=True)
class StoryRoute:
    relationship: StoryRelationship
    candidate: Incident
    classification: StoryRelationshipClassification


class StoryContinuationRouter:
    def __init__(
        self,
        incidents: IncidentRepository,
        *,
        search: StoryCandidateSearch | None = None,
        relationships: StoryRelationshipService | None = None,
    ) -> None:
        self.incidents = incidents
        self.search = search or StoryCandidateSearch(incidents)
        self.relationships = relationships or StoryRelationshipService()

    def route_for_village(
        self,
        *,
        match_result: dict[str, Any] | None,
        message_datetime: datetime,
        candidate_text: str | None,
        candidate_embedding: list[float] | None,
        exclude_raw_message_id: int | None,
        village_id: int | None,
    ) -> StoryRoute | None:
        if village_id is None:
            return None
        scoped_match = match_result or {}
        if not scoped_match.get("village_matches"):
            scoped_match = {
                **scoped_match,
                "village_matches": [{"matched_village_id": village_id}],
            }
        candidates = self.search.find_for_message(
            match_result=scoped_match,
            message_datetime=message_datetime,
            candidate_text=candidate_text,
            candidate_embedding=candidate_embedding,
            exclude_raw_message_id=exclude_raw_message_id,
        )
        village_candidates = [
            candidate
            for candidate in candidates
            if candidate.incident.village_id == village_id
        ]
        classification = self.relationships.classify_best(
            current_text=strip_boilerplate(candidate_text or ""),
            candidates=village_candidates,
        )
        if classification.relationship == StoryRelationship.unrelated:
            return None
        candidate = _candidate_by_id(village_candidates, classification.candidate_incident_id)
        if candidate is None:
            return None
        return StoryRoute(
            relationship=classification.relationship,
            candidate=candidate.incident,
            classification=classification,
        )


def _candidate_by_id(
    candidates: list[StoryCandidate],
    incident_id: UUID | None,
) -> StoryCandidate | None:
    if incident_id is None:
        return None
    for candidate in candidates:
        if candidate.incident.id == incident_id:
            return candidate
    return None
