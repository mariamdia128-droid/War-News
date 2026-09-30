import pytest

from app.core.text_normalization import village_match_key


@pytest.mark.parametrize(
    ("mention", "reference"),
    [
        ("الرمادية", "رمادية"),
        ("الحنية", "حنية"),
        ("الهبارية", "هبّارية"),
        ("عرب الصاليم", "عرب صاليم"),
        ("وادي الحجير", "وادي حجير"),
        ("النبطية الفوقا", "نبطية الفوقا"),
    ],
)
def test_definite_article_folds_on_both_sides(mention: str, reference: str) -> None:
    assert village_match_key(mention) == village_match_key(reference)


def test_compact_key_ignores_spacing_and_article() -> None:
    assert village_match_key("كفر رمان", compact=True) == "كفررمان"
    assert village_match_key("عرب الصاليم", compact=True) == "عربصاليم"


def test_short_stem_is_never_reduced_to_nothing() -> None:
    # "ال" followed by fewer than three letters is not an article.
    assert village_match_key("الله") == "الله"
    assert village_match_key("ال") == "ال"


def test_key_is_idempotent() -> None:
    once = village_match_key("الدير الأحمر")
    assert village_match_key(once) == once


def test_distinct_villages_keep_distinct_keys() -> None:
    assert village_match_key("الخيام") != village_match_key("الخيارة")
    assert village_match_key("زوطر الشرقية") != village_match_key("زوطر الغربية")


@pytest.mark.parametrize(
    ("written", "reference"),
    [
        ("كفررمان", "كفر رمان"),
        ("كفرشوبا", "كفر شوبا"),
        ("كفرتبنيت", "كفر تبنيت"),
        ("ديرسريان", "دير سريان"),
    ],
)
def test_spelling_variants_share_a_compact_key(written: str, reference: str) -> None:
    assert village_match_key(written, compact=True) == village_match_key(
        reference, compact=True
    )
