"""Review-only cross-source duplicate matching for location-bound sub-events."""

from __future__ import annotations

from datetime import datetime

from app.core.config import settings
from app.news.models import Incident, MatchStatus
from app.news.repositories.incident_repository import (
    IncidentRepository,
    SegmentReviewSource,
)


class SegmentReviewDedupService:
    def __init__(
        self,
        incidents: IncidentRepository,
        *,
        similarity_threshold: float | None = None,
        window_days: int | None = None,
        max_candidates: int | None = None,
    ) -> None:
        self.incidents = incidents
        self.similarity_threshold = float(
            settings.segment_dedup_review_similarity_threshold
            if similarity_threshold is None
            else similarity_threshold
        )
        self.window_days = int(
            settings.segment_dedup_review_window_days
            if window_days is None
            else window_days
        )
        self.max_candidates = int(
            settings.segment_dedup_review_max_candidates
            if max_candidates is None
            else max_candidates
        )

    def queue_for_incident(
        self,
        *,
        incident: Incident,
        raw_message_id: int,
        source_id: int,
        event_datetime: datetime,
        segment_text: str | None,
        source_name: str | None = None,
        source_platform: str | None = None,
    ) -> int:
        """Queue pending soft matches only; this path never merges incidents."""
        if (
            incident.id is None
            or incident.village_id is None
            or incident.condition_id is None
            or not segment_text
            or not segment_text.strip()
        ):
            return 0

        sources = self.incidents.find_segment_review_sources(
            village_id=incident.village_id,
            condition_id=incident.condition_id,
            source_id=source_id,
            source_name=source_name,
            source_platform=source_platform,
            event_date=event_datetime.date(),
            window_days=self.window_days,
            exclude_raw_message_id=raw_message_id,
            max_results=self.max_candidates,
        )
        queued = 0
        highest_score = 0.0
        for source in sources:
            target_segments = self._location_bound_segments(source)
            if not target_segments:
                continue
            score = max(
                self.incidents.segment_text_similarity(segment_text, target)
                for target in target_segments
            )
            if score < self.similarity_threshold:
                continue
            if self.incidents.has_pending_segment_review_match(
                incident_id=incident.id,
                matched_incident_id=source.incident.id,
            ):
                continue
            self.incidents.create_duplicate_match(
                incident=incident,
                matched_incident=source.incident,
                similarity_score=score,
                status=MatchStatus.pending,
            )
            highest_score = max(highest_score, score)
            queued += 1

        if queued:
            incident.duplicate_flag = True
            incident.duplicate_level = "segment"
            incident.duplicate_similarity_score = highest_score
            incident.verification_status = "needs_verification"
            incident.verification_reason = (
                "Possible cross-source duplicate segment; human confirmation "
                f"required (best similarity {highest_score:.2f})."
            )
            self.incidents.db.commit()
        return queued

    @staticmethod
    def _location_bound_segments(source: SegmentReviewSource) -> list[str]:
        sub_events = source.extraction_result.get("sub_events")
        village_matches = source.match_result.get("village_matches")
        if not isinstance(sub_events, list) or not isinstance(village_matches, list):
            return []

        indexes: set[int] = set()
        for match in village_matches:
            if not isinstance(match, dict):
                continue
            event_index = match.get("event_index")
            if not isinstance(event_index, int) or isinstance(event_index, bool):
                continue
            if match.get("matched_village_id") != source.incident.village_id:
                continue
            matched_condition_id = match.get("matched_condition_id")
            if (
                matched_condition_id is not None
                and matched_condition_id != source.incident.condition_id
            ):
                continue
            indexes.add(event_index)

        segments: list[str] = []
        for index in sorted(indexes):
            if not 0 <= index < len(sub_events):
                continue
            sub_event = sub_events[index]
            if not isinstance(sub_event, dict) or not sub_event.get("locations"):
                continue
            text = sub_event.get("evidence_span") or sub_event.get("action_text")
            if isinstance(text, str) and text.strip():
                segments.append(text.strip())
        return segments
