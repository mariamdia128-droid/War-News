"""Review-only cross-source duplicate matching for location-bound sub-events."""

from __future__ import annotations

import re
from datetime import datetime, time

from app.core.config import settings
from app.news.models import Incident, MatchStatus
from app.news.repositories.incident_repository import (
    IncidentRepository,
    SegmentReviewSource,
)


ROUNDUP_MARKERS = (
    "ملخص",
    "حصيلة الاعتداءات",
    "الاعتداءات التي طالت",
    "منذ منتصف الليل",
    "حتى الساعة",
    "صفحة الإعلامي الشهيد علي شعيب",
)

_ARABIC_TOKEN_RE = re.compile(r"[\u0621-\u064a]+")
_GENERIC_TOKENS = frozenset(
    {
        "في", "على", "الى", "إلى", "عن", "من", "مع", "كما", "بعد", "قبل",
        "بلدة", "بلدتي", "بلدات", "قرية", "قرى", "اطراف", "أطراف", "محيط",
    }
)

_EVENT_BINDING_MARKERS = (
    "استهدف",
    "استهدفت",
    "يستهدف",
    "تستهدف",
    "إطلاق نار",
    "اطلاق نار",
    "إطلاق قذائف",
    "اطلاق قذائف",
    "تعرضت",
    "تعرض",
    "تحرك",
    "انفجار",
    "سقوط",
    "تجدد",
)

_NON_TARGET_CONJUNCTION_PREFIXES = (
    "إطلاق", "اطلاق", "أجواء", "اجواء", "تمشيط", "قصف", "غارة", "غارات",
    "تجدد", "تحرك", "كما", "عمد", "سقوط", "انفجار",
)

_MODIFIER_GROUPS: dict[str, tuple[str, ...]] = {
    "phosphorus": ("فوسفور", "فسفور", "فوسفوري", "فسفوري"),
    "tank": ("دبابة", "ميركافا", "قذائف دبابة"),
    "machine_gun": ("رشاش", "رشاشة", "أسلحة رشاشة", "تمشيط"),
    "drone": ("مسيرة", "مسيّرة", "طائرة مسيرة", "طائرة مسيّرة"),
}


def distinct_target_village_count(matches: list[dict]) -> int:
    """Shared persisted-match signal used by materialization and review policy."""
    return len(
        {
            match.get("matched_village_id")
            for match in matches
            if isinstance(match, dict)
            and match.get("village_role", "target") == "target"
            and isinstance(match.get("matched_village_id"), int)
            and not isinstance(match.get("matched_village_id"), bool)
        }
    )


class SegmentReviewDedupService:
    def __init__(
        self,
        incidents: IncidentRepository,
        *,
        similarity_threshold: float | None = None,
        window_days: int | None = None,
        max_candidates: int | None = None,
        max_event_gap_hours: int | None = None,
        min_informative_tokens: int | None = None,
    ) -> None:
        self.incidents = incidents
        self.similarity_threshold = float(
            settings.segment_dedup_review_balanced_score_threshold
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
        self.max_event_gap_hours = int(
            settings.segment_dedup_review_max_event_gap_hours
            if max_event_gap_hours is None
            else max_event_gap_hours
        )
        self.min_informative_tokens = int(
            settings.segment_dedup_review_min_informative_tokens
            if min_informative_tokens is None
            else min_informative_tokens
        )

    def queue_for_incident(
        self,
        *,
        incident: Incident,
        raw_message_id: int,
        source_id: int,
        event_datetime: datetime,
        segment_text: str | None,
        raw_text: str | None = None,
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
            event_datetime=event_datetime,
            window_days=self.window_days,
            max_event_gap_hours=self.max_event_gap_hours,
            exclude_raw_message_id=raw_message_id,
            max_results=self.max_candidates,
        )
        queued = 0
        highest_score = 0.0
        for source in sources:
            if not self._is_earlier_source(
                source,
                current_datetime=event_datetime,
                current_raw_message_id=raw_message_id,
            ):
                continue
            if self._is_roundup_source(source):
                continue
            current_segments = [segment_text]
            if raw_text and raw_text.strip() and raw_text.strip() != segment_text.strip():
                current_segments.append(raw_text.strip())
            target_segments = self._location_bound_segments(source)
            if source.raw_text and source.raw_text.strip() not in target_segments:
                target_segments.append(source.raw_text.strip())
            if not target_segments:
                continue
            scores = [
                self.incidents.segment_text_similarity(current, target)
                for current in current_segments
                for target in target_segments
                if self._is_informative_segment(current)
                and self._is_informative_segment(target)
                and not self._has_modifier_conflict(current, target)
                and not self._has_named_target_conflict(current, target)
            ]
            if not scores:
                continue
            score = max(scores)
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
            self.incidents.db.commit()
        return queued

    def _is_earlier_source(
        self,
        source: SegmentReviewSource,
        *,
        current_datetime: datetime,
        current_raw_message_id: int,
    ) -> bool:
        candidate_datetime = source.message_datetime
        if candidate_datetime is None:
            candidate_datetime = datetime.combine(
                source.incident.event_date,
                source.incident.event_time or time(0, 0),
            )
        if current_datetime.tzinfo is not None and candidate_datetime.tzinfo is None:
            current_datetime = current_datetime.replace(tzinfo=None)
        elif current_datetime.tzinfo is None and candidate_datetime.tzinfo is not None:
            candidate_datetime = candidate_datetime.replace(tzinfo=None)
        gap_seconds = (current_datetime - candidate_datetime).total_seconds()
        if gap_seconds < 0 or gap_seconds > self.max_event_gap_hours * 3600:
            return False
        if gap_seconds == 0:
            candidate_raw_id = source.incident.raw_message_id
            return candidate_raw_id is not None and candidate_raw_id < current_raw_message_id
        return True

    @staticmethod
    def _is_roundup_source(source: SegmentReviewSource) -> bool:
        matches = source.match_result.get("village_matches") or []
        matched_target_count = distinct_target_village_count(matches)
        extracted_targets = {
            " ".join(str(location.get("village") or "").split()).strip()
            for event in (source.extraction_result.get("sub_events") or [])
            if isinstance(event, dict)
            for location in (event.get("locations") or [])
            if isinstance(location, dict)
            and location.get("role", "target") == "target"
            and str(location.get("village") or "").strip()
        }
        # Multiple actions in one place are one single-village report, not a
        # roundup. Only a broad place list (three or more distinct targets) is
        # sufficient without an explicit summary/page-post marker.
        distinct_place_count = matched_target_count or len(extracted_targets)
        if distinct_place_count >= 3:
            return True
        text = source.raw_text or ""
        return any(marker in text for marker in ROUNDUP_MARKERS) or text.count("•") >= 2

    def _is_informative_segment(self, text: str) -> bool:
        tokens = _ARABIC_TOKEN_RE.findall(text)
        informative = [token for token in tokens if token not in _GENERIC_TOKENS]
        has_action = any(
            marker in text
            for marker in (
                "قصف", "غارة", "غارات", "استهدف", "استهداف", "تمشيط", "قذائف",
                "دبابة", "دبابات", "إطلاق نار", "اطلاق نار", "تحرك", "تعرض",
            )
        )
        binds_action_to_event = any(marker in text for marker in _EVENT_BINDING_MARKERS)
        return (
            has_action
            and binds_action_to_event
            and len(informative) >= self.min_informative_tokens
        )

    @staticmethod
    def _has_modifier_conflict(left: str, right: str) -> bool:
        def present(text: str) -> set[str]:
            return {
                name
                for name, markers in _MODIFIER_GROUPS.items()
                if any(marker in text for marker in markers)
            }

        left_modifiers = present(left)
        right_modifiers = present(right)
        return bool(left_modifiers and right_modifiers and left_modifiers.isdisjoint(right_modifiers))

    @staticmethod
    def _has_named_target_conflict(left: str, right: str) -> bool:
        # Only explicit secondary targets are compared. Absence on either side
        # is deliberately not a conflict because terse reports omit detail.
        target_pattern = re.compile(
            r"(?:،\s*|(?:^|\s)و\s*)"
            r"([\u0621-\u064a]+(?:\s+[\u0621-\u064a]+){0,2})"
        )
        left_targets = {value.strip() for value in target_pattern.findall(left)}
        right_targets = {value.strip() for value in target_pattern.findall(right)}
        left_targets = {
            value
            for value in left_targets
            if not value.startswith(_NON_TARGET_CONJUNCTION_PREFIXES)
        }
        right_targets = {
            value
            for value in right_targets
            if not value.startswith(_NON_TARGET_CONJUNCTION_PREFIXES)
        }
        return bool(left_targets and right_targets and left_targets.isdisjoint(right_targets))

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
            evidence = sub_event.get("evidence_span")
            action = sub_event.get("action_text")
            if isinstance(evidence, str) and evidence.strip():
                text = evidence.strip()
                if isinstance(action, str) and action.strip() and action.strip() not in text:
                    text = f"{action.strip()} {text}"
                segments.append(text)
            elif isinstance(action, str) and action.strip():
                segments.append(action.strip())
        return segments
