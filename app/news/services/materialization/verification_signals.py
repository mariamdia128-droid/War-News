from __future__ import annotations


LOW_CONFIDENCE_VILLAGE_REVIEW_REASON = (
    "Low-confidence village match requires manual review."
)

LOW_CONFIDENCE_VILLAGE = "low_confidence_village"
CONDITION_REVIEW = "condition_review"
CASUALTY_ALLOCATION = "casualty_allocation"
TIER2_RETRY_CAP = "tier2_retry_cap"
CASUALTY_TRANSITION_CONFLICT = "casualty_transition_conflict"
STORY_REVISION_REVIEW = "story_revision_review"


def _is_weak_village(item: object) -> bool:
    return isinstance(item, dict) and bool(
        item.get("village_review_required")
        or item.get("village_match_status") == "matched_low_confidence"
    )


def _village_signal(
    match: dict,
    village_matches: list,
    village_id: int | None,
) -> bool:
    """True when the village evidence calls for review of this incident."""
    if village_id is None:
        return bool(match.get("any_village_low_confidence")) or any(
            _is_weak_village(item) for item in village_matches
        )
    own = [
        item
        for item in village_matches
        if isinstance(item, dict) and item.get("matched_village_id") == village_id
    ]
    # A weak mention only counts when no other mention of the same village
    # resolved confidently.
    if own and all(_is_weak_village(item) for item in own):
        return True
    # A village with no id never gets an incident of its own, so if it carries
    # casualties the bulletin's incidents stay flagged rather than losing it.
    return any(
        isinstance(item, dict)
        and item.get("matched_village_id") is None
        and (item.get("deaths") or item.get("injuries"))
        for item in village_matches
    )


def active_non_duplicate_verification_reasons(
    *,
    match_result: dict | None = None,
    extraction_result: dict | None = None,
    tier2_retry_count: int = 0,
    tier2_retry_limit: int | None = None,
    verification_reason: str | None = None,
    low_confidence_village_match: bool = False,
    condition_review_required: bool = False,
    village_id: int | None = None,
) -> frozenset[str]:
    """Derive every active non-duplicate review reason from stored signals.

    ``village_id`` is the incident's own village. When given, the village signal
    is read from that village's matches only, so a sibling incident from the same
    multi-village bulletin is not flagged for another village's weak match. When
    omitted (bulletin-level callers) any weak village counts, as before.
    """
    reasons: set[str] = set()
    match = match_result or {}
    extraction = extraction_result or {}
    village_matches = match.get("village_matches") or []
    if low_confidence_village_match or _village_signal(
        match, village_matches, village_id
    ):
        reasons.add(LOW_CONFIDENCE_VILLAGE)
    if condition_review_required or match.get("condition_review_required") or any(
        isinstance(item, dict) and item.get("condition_review_required")
        for item in village_matches
    ):
        reasons.add(CONDITION_REVIEW)
    if (
        extraction.get("casualty_scope_needs_review")
        or extraction.get("casualty_scope_review_reason")
        or extraction.get("category_casualties_suppressed")
    ):
        reasons.add(CASUALTY_ALLOCATION)
    if tier2_retry_limit is not None and tier2_retry_count >= tier2_retry_limit:
        reasons.add(TIER2_RETRY_CAP)

    stored = (verification_reason or "").strip().casefold()
    if stored and not stored.startswith(("possible duplicate", "possible cross-source duplicate")):
        if stored == LOW_CONFIDENCE_VILLAGE_REVIEW_REASON.casefold():
            reasons.add(LOW_CONFIDENCE_VILLAGE)
        elif "condition" in stored:
            reasons.add(CONDITION_REVIEW)
        elif stored.startswith(("category casualties", "unsupported casualty_scope")):
            reasons.add(CASUALTY_ALLOCATION)
        elif stored.startswith("tier 2 detail extraction failed"):
            reasons.add(TIER2_RETRY_CAP)
        elif "casualty count conflict" in stored or "casualty transition" in stored:
            reasons.add(CASUALTY_TRANSITION_CONFLICT)
        elif "story revision" in stored:
            reasons.add(STORY_REVISION_REVIEW)
        else:
            # Unknown stored non-duplicate reasons remain review-worthy rather
            # than being erased by a duplicate decision.
            reasons.add("stored_review_reason")
    return frozenset(reasons)


def _verification_reason(
    match_result: dict | None,
    *,
    duplicate_flag: bool = False,
    duplicate_level: str | None = None,
    duplicate_similarity_score: float | None = None,
    insufficient_score: bool = False,
    low_confidence_village_match: bool = False,
    condition_review_reason: str | None = None,
) -> str | None:
    """Return a plain-language review reason for unresolved review signals."""
    if condition_review_reason:
        return condition_review_reason
    if low_confidence_village_match:
        return LOW_CONFIDENCE_VILLAGE_REVIEW_REASON
    if duplicate_flag:
        if duplicate_level is not None and duplicate_similarity_score is not None:
            return (
                "Possible duplicate of an existing incident "
                f"(similarity {duplicate_level}, score {duplicate_similarity_score:.2f})."
            )
        return (
            "Possible duplicate of an existing incident — flagged during "
            "fast-path matching."
        )
    if insufficient_score:
        return (
            "Possible duplicate of an existing incident — flagged during "
            "fast-path matching."
        )
    return None
