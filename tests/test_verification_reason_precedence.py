from app.news.services.materialization.verification_signals import (
    LOW_CONFIDENCE_VILLAGE_REVIEW_REASON,
    _verification_reason,
)


def test_hard_reasons_precede_condition_hint_and_are_all_preserved() -> None:
    reason = _verification_reason(
        {},
        duplicate_flag=True,
        duplicate_level="medium",
        duplicate_similarity_score=0.72,
        low_confidence_village_match=True,
        hard_reasons=(
            "Aggregate casualty toll across multiple locations has no per-location breakdown.",
            "Flare wording appears together with strike language.",
        ),
        condition_review_reason=(
            "Low-confidence condition text match requires review (text: قصف)."
        ),
    )
    assert reason is not None
    parts = reason.split("; ")
    assert parts[0].startswith("Possible duplicate")
    assert parts[1].startswith("Aggregate casualty")
    assert parts[2].startswith("Flare wording")
    assert parts[3] == LOW_CONFIDENCE_VILLAGE_REVIEW_REASON
    assert parts[4].startswith("Low-confidence condition")


def test_duplicate_reason_is_not_hidden_by_condition_hint() -> None:
    reason = _verification_reason(
        {}, duplicate_flag=True, condition_review_reason="condition info"
    )
    assert reason is not None
    assert reason.startswith("Possible duplicate")
    assert reason.endswith("; condition info")


def test_duplicate_hard_reason_is_not_repeated() -> None:
    reason = _verification_reason(
        {}, duplicate_flag=True, insufficient_score=True
    )
    assert reason is not None
    assert reason.count("Possible duplicate") == 1
