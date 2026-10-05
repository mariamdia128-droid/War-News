from scripts.recompute_verification_status import (
    _preserved_hard_reasons,
    _reason_bucket,
)


def test_soft_condition_reason_is_not_preserved_as_hard() -> None:
    assert _preserved_hard_reasons(
        "Low-confidence condition text match requires review (text: قصف)."
    ) == []


def test_hard_merge_and_cross_source_reasons_are_preserved() -> None:
    cross = "Possible cross-source duplicate segment; human confirmation required"
    merge = "Possible duplicate — casualty count conflict detected during merge"
    assert _preserved_hard_reasons(cross) == [cross]
    assert _preserved_hard_reasons(merge) == [merge]


def test_reason_buckets_collapse_expected_legacy_reasons() -> None:
    assert _reason_bucket(None) == "[NULL/empty]"
    assert _reason_bucket("Unsupported casualty_scope=x") == "Unsupported casualty scope"
    assert _reason_bucket(
        "Low-confidence condition text match requires review (text: غارة)."
    ) == "Low-confidence condition"
