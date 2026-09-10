from app.news.repositories.incident_repository import IncidentRepository
from app.news.services.materialization.verification_signals import (
    LOW_CONFIDENCE_VILLAGE_REVIEW_REASON,
)


def test_casualty_review_reasons_remain_user_visible() -> None:
    assert IncidentRepository._is_casualty_review_reason(
        "Category casualties require manual per-village confirmation"
    )
    assert IncidentRepository._is_casualty_review_reason(
        "Unsupported casualty_scope=bulletin_aggregate: evidence matched 1 target village(s)"
    )
    assert not IncidentRepository._is_casualty_review_reason(
        "Possible duplicate detected during detail extraction"
    )


def test_low_confidence_village_review_reason_remains_user_visible() -> None:
    assert IncidentRepository._should_keep_needs_verification_after_duplicate_clear(
        LOW_CONFIDENCE_VILLAGE_REVIEW_REASON
    )
