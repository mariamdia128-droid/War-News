from datetime import datetime, timezone

from app.llm.dtos import CasualtyScope, ExtractionCasualties, ExtractionResult
from app.news.services.incident_details.category_mapper import (
    suppress_category_casualties,
)
from app.news.services.materialization.verification_signals import (
    AGGREGATE_CASUALTY_REVIEW_REASON,
    VAGUE_CASUALTY_REVIEW_REASON,
    casualty_review_reason,
)


def _extraction(**updates) -> ExtractionResult:
    base = ExtractionResult(
        is_relevant=True,
        village=["A"],
        casualties=ExtractionCasualties(),
        model="test",
        extracted_at=datetime.now(timezone.utc),
    )
    return base.model_copy(update=updates)


def test_zero_casualties_never_require_scope_review() -> None:
    extraction = _extraction(
        casualty_scope=CasualtyScope.bulletin_aggregate,
        casualty_scope_needs_review=True,
        casualty_scope_review_reason=(
            "Unsupported casualty_scope=bulletin_aggregate: evidence matched 0 target village(s)"
        ),
    )
    assert casualty_review_reason(extraction, target_count=3) is None


def test_exact_single_village_does_not_require_review() -> None:
    extraction = _extraction(
        casualties=ExtractionCasualties(deaths=2),
        casualty_status="exact",
        casualty_scope=CasualtyScope.per_village_exact,
    )
    assert casualty_review_reason(extraction, target_count=1) is None


def test_aggregate_single_target_is_effectively_per_village() -> None:
    extraction = _extraction(
        casualties=ExtractionCasualties(total_injuries=3),
        casualty_status="exact",
        casualty_scope=CasualtyScope.bulletin_aggregate,
    )
    assert casualty_review_reason(extraction, target_count=1) is None


def test_positive_multi_target_aggregate_without_breakdown_requires_review() -> None:
    extraction = _extraction(
        village=["A", "B"],
        casualties=ExtractionCasualties(total_deaths=2, total_injuries=6),
        casualty_status="aggregate_only",
        casualty_scope=CasualtyScope.bulletin_aggregate,
    )
    assert (
        casualty_review_reason(extraction, target_count=2)
        == AGGREGATE_CASUALTY_REVIEW_REASON
    )


def test_vague_casualty_wording_requires_review() -> None:
    extraction = _extraction(casualty_status="count_missing")
    assert casualty_review_reason(extraction, target_count=1) == VAGUE_CASUALTY_REVIEW_REASON


def test_category_suppression_only_flags_positive_counts() -> None:
    cleared_zero, zero_review = suppress_category_casualties({"carm_d": 0})
    cleared_positive, positive_review = suppress_category_casualties({"carm_d": 2})
    assert cleared_zero["carm_d"] is None
    assert zero_review is False
    assert cleared_positive["carm_d"] is None
    assert positive_review is True
