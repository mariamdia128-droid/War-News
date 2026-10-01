
from app.news.services.materialization.incident_materialization_service import (
    _initial_verification_status,
)
from app.news.services.materialization.verification_signals import (
    LOW_CONFIDENCE_VILLAGE,
    active_non_duplicate_verification_reasons,
)


def _vm(village_id, status="matched", **extra):
    return {
        "matched_village_id": village_id,
        "village_match_status": status,
        "village_review_required": status != "matched",
        **extra,
    }


def _bulletin(*matches, any_low=None):
    low = any(m["village_match_status"] != "matched" for m in matches)
    return {
        "village_matches": list(matches),
        "any_village_low_confidence": low if any_low is None else any_low,
    }


def test_sibling_with_confident_village_is_not_flagged_for_another_villages_match():
    match = _bulletin(_vm(1), _vm(2, "matched_low_confidence"))

    confident = active_non_duplicate_verification_reasons(
        match_result=match, village_id=1
    )
    weak = active_non_duplicate_verification_reasons(match_result=match, village_id=2)

    assert LOW_CONFIDENCE_VILLAGE not in confident
    assert LOW_CONFIDENCE_VILLAGE in weak


def test_without_a_village_id_any_weak_village_still_counts():
    match = _bulletin(_vm(1), _vm(2, "matched_low_confidence"))

    reasons = active_non_duplicate_verification_reasons(match_result=match)

    assert LOW_CONFIDENCE_VILLAGE in reasons


def test_unresolved_village_with_casualties_keeps_siblings_flagged():
    match = _bulletin(_vm(1), _vm(None, "unmatched", deaths=2))

    reasons = active_non_duplicate_verification_reasons(
        match_result=match, village_id=1
    )

    assert LOW_CONFIDENCE_VILLAGE in reasons


def test_unresolved_village_without_casualties_does_not_flag_siblings():
    match = _bulletin(_vm(1), _vm(None, "unmatched"))

    reasons = active_non_duplicate_verification_reasons(
        match_result=match, village_id=1
    )

    assert LOW_CONFIDENCE_VILLAGE not in reasons


def test_one_confident_mention_of_a_village_outweighs_a_weak_duplicate_mention():
    match = _bulletin(_vm(1, "matched_low_confidence"), _vm(1))

    reasons = active_non_duplicate_verification_reasons(
        match_result=match, village_id=1
    )

    assert LOW_CONFIDENCE_VILLAGE not in reasons


def test_incident_status_is_per_village_in_a_mixed_bulletin():
    match = _bulletin(_vm(1), _vm(2, "matched_low_confidence"))

    assert _initial_verification_status(match, village_id=1) == "auto_processed"
    assert (
        _initial_verification_status(
            match, village_id=2, low_confidence_village_match=True
        )
        == "needs_verification"
    )


