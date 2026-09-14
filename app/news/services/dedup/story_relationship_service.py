"""Classify a new message against a prior story candidate.

Pairwise on purpose: ``casualty_scope`` / ``casualty_transitions`` are produced
inside single-message Tier-1 extraction, then validated by a deterministic
backstop. Story relationship cannot live on ``ExtractionResult`` because it
requires a specific prior incident. This service follows the same
typed-result + keyword backstop + downgrade-on-unsupported-claim pattern.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.core.text_normalization import normalize_arabic_text
from app.llm.dtos import StoryRelationship, StoryRelationshipClassification
from app.news.services.incident_details.story_revision_backstop import (
    detect_story_revision_backstop,
)

_HOUSE_RE = re.compile(r"منزل|بيت|مبنى|بنايه|شقه")
_CAR_RE = re.compile(r"سيار|دراج")
_SPARSE_RE = re.compile(r"اصابات|ضحايا|وقوع")
_DIGIT_RE = re.compile(r"[0-9٠-٩]")

LlmClassifyFn = Callable[
    [str, str],
    StoryRelationshipClassification,
]


class StoryRelationshipService:
    def __init__(self, llm_classify: LlmClassifyFn | None = None) -> None:
        self.llm_classify = llm_classify

    def classify(
        self,
        *,
        current_text: str | None,
        candidate_text: str | None,
        candidate_incident_id: UUID | None,
        candidate_deaths: int | None = None,
        candidate_injuries: int | None = None,
        embedding_similarity: float | None = None,
        claimed_relationship: StoryRelationship | None = None,
        claimed_evidence: str | None = None,
    ) -> StoryRelationshipClassification:
        if claimed_relationship == StoryRelationship.revision and candidate_incident_id is None:
            return StoryRelationshipClassification(
                relationship=StoryRelationship.unrelated,
                relationship_evidence=claimed_evidence,
                needs_review=True,
                review_reason="Unsupported story revision: no candidate incident in window",
                candidate_incident_id=None,
            )

        backstop = detect_story_revision_backstop(
            current_text,
            candidate_text=candidate_text,
            candidate_deaths=candidate_deaths,
            candidate_injuries=candidate_injuries,
        )
        if backstop.plausible and backstop.relationship_hint == "revision":
            if candidate_incident_id is None:
                return StoryRelationshipClassification(
                    relationship=StoryRelationship.unrelated,
                    relationship_evidence=backstop.evidence,
                    needs_review=True,
                    review_reason="Unsupported story revision: no candidate incident in window",
                    matched_keywords=backstop.matched_keywords,
                )
            return StoryRelationshipClassification(
                relationship=StoryRelationship.revision,
                relationship_evidence=backstop.evidence,
                candidate_incident_id=candidate_incident_id,
                matched_keywords=backstop.matched_keywords,
            )

        llm_result: StoryRelationshipClassification | None = None
        if self.llm_classify is not None and current_text and candidate_text:
            llm_result = self.llm_classify(current_text, candidate_text)
            if (
                llm_result.relationship == StoryRelationship.revision
                and candidate_incident_id is None
            ):
                return StoryRelationshipClassification(
                    relationship=StoryRelationship.unrelated,
                    relationship_evidence=llm_result.relationship_evidence,
                    needs_review=True,
                    review_reason="Unsupported story revision: no candidate incident in window",
                    candidate_incident_id=None,
                )
            if llm_result.relationship != StoryRelationship.unrelated:
                return llm_result.model_copy(
                    update={"candidate_incident_id": candidate_incident_id}
                )

        if claimed_relationship is not None:
            if (
                claimed_relationship == StoryRelationship.revision
                and candidate_incident_id is None
            ):
                return StoryRelationshipClassification(
                    relationship=StoryRelationship.unrelated,
                    relationship_evidence=claimed_evidence,
                    needs_review=True,
                    review_reason="Unsupported story revision: no candidate incident in window",
                )
            return StoryRelationshipClassification(
                relationship=claimed_relationship,
                relationship_evidence=claimed_evidence,
                candidate_incident_id=candidate_incident_id,
            )

        return self._heuristic(
            current_text=current_text,
            candidate_text=candidate_text,
            candidate_incident_id=candidate_incident_id,
            embedding_similarity=embedding_similarity,
        )

    def classify_best(
        self,
        *,
        current_text: str | None,
        candidates: list[Any],
    ) -> StoryRelationshipClassification:
        """Pick the strongest non-unrelated classification among candidates."""
        if not candidates:
            backstop = detect_story_revision_backstop(current_text)
            if backstop.plausible:
                return StoryRelationshipClassification(
                    relationship=StoryRelationship.unrelated,
                    relationship_evidence=backstop.evidence,
                    needs_review=True,
                    review_reason="Unsupported story revision: no candidate incident in window",
                    matched_keywords=backstop.matched_keywords,
                )
            return StoryRelationshipClassification(
                relationship=StoryRelationship.unrelated,
                relationship_evidence=None,
            )

        ranked: list[StoryRelationshipClassification] = []
        for candidate in candidates:
            incident = candidate.incident
            ranked.append(
                self.classify(
                    current_text=current_text,
                    candidate_text=getattr(incident, "khabar", None),
                    candidate_incident_id=getattr(incident, "id", None),
                    candidate_deaths=getattr(incident, "deaths", None)
                    or getattr(incident, "total_deaths", None),
                    candidate_injuries=getattr(incident, "injuries", None)
                    or getattr(incident, "total_injuries", None),
                    embedding_similarity=getattr(candidate, "embedding_similarity", None),
                )
            )
        ranked.sort(key=lambda item: _relationship_rank(item, candidates))
        return ranked[0]


    def _heuristic(
        self,
        *,
        current_text: str | None,
        candidate_text: str | None,
        candidate_incident_id: UUID | None,
        embedding_similarity: float | None,
    ) -> StoryRelationshipClassification:
        current_bucket = _action_bucket(current_text)
        candidate_bucket = _action_bucket(candidate_text)
        embedding = embedding_similarity or 0.0
        current_sparse = _is_sparse(current_text)

        if current_sparse and embedding >= 0.40 and candidate_incident_id is not None:
            return StoryRelationshipClassification(
                relationship=StoryRelationship.revision,
                relationship_evidence="sparse early report of the same village event",
                candidate_incident_id=candidate_incident_id,
            )

        if (
            current_bucket in {"car", "house"}
            and current_bucket == candidate_bucket
            and embedding >= 0.55
        ):
            return StoryRelationshipClassification(
                relationship=StoryRelationship.duplicate,
                relationship_evidence=f"same {current_bucket} action",
                candidate_incident_id=candidate_incident_id,
            )

        if (
            {current_bucket, candidate_bucket} == {"car", "house"}
            and embedding >= 0.55
        ):
            return StoryRelationshipClassification(
                relationship=StoryRelationship.distinct_sub_event,
                relationship_evidence="related house vs car actions at same place",
                candidate_incident_id=candidate_incident_id,
            )

        if current_bucket == "car" and candidate_bucket == "mixed" and embedding >= 0.55:
            return StoryRelationshipClassification(
                relationship=StoryRelationship.distinct_sub_event,
                relationship_evidence="car strike vs mixed house+car bulletin",
                candidate_incident_id=candidate_incident_id,
            )

        if embedding >= 0.70:
            return StoryRelationshipClassification(
                relationship=StoryRelationship.duplicate,
                relationship_evidence="high embedding similarity",
                candidate_incident_id=candidate_incident_id,
            )

        return StoryRelationshipClassification(
            relationship=StoryRelationship.unrelated,
            relationship_evidence=None,
            candidate_incident_id=candidate_incident_id,
        )


def _action_bucket(text: str | None) -> str:
    normalized = normalize_arabic_text(text or "")
    has_car = bool(_CAR_RE.search(normalized))
    has_house = bool(_HOUSE_RE.search(normalized))
    if has_car and has_house:
        return "mixed"
    if has_car:
        return "car"
    if has_house:
        return "house"
    return "other"


def _is_sparse(text: str | None) -> bool:
    normalized = normalize_arabic_text(text or "")
    if not normalized:
        return False
    if _DIGIT_RE.search(normalized) and not _SPARSE_RE.search(normalized):
        return False
    return bool(_SPARSE_RE.search(normalized)) or not _DIGIT_RE.search(normalized)


_RANK = {
    StoryRelationship.revision: 0,
    StoryRelationship.duplicate: 1,
    StoryRelationship.distinct_sub_event: 2,
    StoryRelationship.unrelated: 3,
}


def _relationship_rank(item: StoryRelationshipClassification, candidates: list[Any]) -> tuple:
    embedding = 0.0
    for candidate in candidates:
        if getattr(candidate.incident, "id", None) == item.candidate_incident_id:
            embedding = float(getattr(candidate, "embedding_similarity", None) or 0.0)
            break
    # Prefer car-only duplicates over mixed-bulletin distinct_sub_event when
    # both exist; rank already puts duplicate ahead of distinct_sub_event.
    return (_RANK[item.relationship], -embedding)
