"""Wide-window, condition-agnostic story-continuation candidate search.

Shares the village-set primitive used by bulletin reconciliation
(``village_ids_from_match_result``) rather than introducing a second
village-overlap matcher. Unlike bulletin reconciliation this path ranks by
message ``content_embedding`` / incident ``khabar_embedding`` cosine
similarity and does not require condition equality.

Embeddings are populated on ``raw_messages.content_embedding`` in the
embedding sweep (384-d ``paraphrase-multilingual-MiniLM-L12-v2``) *before*
fast-path materialization, which waits up to
``fast_path_embedding_wait_minutes``. Incidents copy that vector onto
``khabar_embedding`` at insert time, so candidate search can use it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.config import settings
from app.news.repositories.incident_repository import (
    IncidentRepository,
    StoryCandidate,
)
from app.news.services.clustering.clustering_service import (
    village_ids_from_match_result,
)
from app.news.services.clustering.raw_message_embedding_service import (
    strip_boilerplate,
)
from app.news.services.incident_details.story_revision_backstop import (
    has_story_revision_recall_markers,
)


class StoryCandidateSearch:
    def __init__(self, incident_repository: IncidentRepository) -> None:
        self.incidents = incident_repository

    def find_for_message(
        self,
        *,
        match_result: dict[str, Any] | None,
        message_datetime: datetime,
        candidate_text: str | None,
        candidate_embedding: list[float] | None,
        exclude_raw_message_id: int | None,
        window_hours: int | None = None,
        embedding_threshold: float | None = None,
        max_results: int | None = None,
    ) -> list[StoryCandidate]:
        village_ids = set(village_ids_from_match_result(match_result))
        if not village_ids:
            return []
        query = {
            "village_ids": village_ids,
            "message_datetime": message_datetime,
            "window_hours": (
                window_hours
                if window_hours is not None
                else settings.story_candidate_window_hours
            ),
            "max_results": (
                max_results
                if max_results is not None
                else settings.story_candidate_max_results
            ),
            "candidate_text": strip_boilerplate(candidate_text or "") or None,
            "candidate_embedding": candidate_embedding,
            "exclude_raw_message_id": exclude_raw_message_id,
        }
        threshold = (
            embedding_threshold
            if embedding_threshold is not None
            else settings.story_candidate_embedding_threshold
        )
        found = self.incidents.find_story_candidates(
            **query,
            embedding_threshold=threshold,
        )
        if (
            embedding_threshold is None
            and has_story_revision_recall_markers(candidate_text)
            and len(found) < query["max_results"]
        ):
            extra = self.incidents.find_story_candidates(
                **query,
                embedding_threshold=0.0,
            )
            found = _merge_story_candidates(found, extra, query["max_results"])
        return found


def _merge_story_candidates(
    primary: list[StoryCandidate],
    extra: list[StoryCandidate],
    max_results: int,
) -> list[StoryCandidate]:
    by_id = {candidate.incident.id: candidate for candidate in primary}
    for candidate in extra:
        by_id.setdefault(candidate.incident.id, candidate)
    merged = sorted(
        by_id.values(),
        key=lambda item: item.embedding_similarity or 0.0,
        reverse=True,
    )
    return merged[:max_results]
