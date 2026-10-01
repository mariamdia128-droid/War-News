import pytest

from app.news.services.air_violations.air_violation_eligibility import (
    evaluate_air_violation_text,
)


@pytest.mark.parametrize("text", [
    "غارة على منزل في صور",
    "غارات استهدفت النبطية",
    "استهداف سيارة في ميفدون",
    "قصفت المدفعية أطراف البلدة",
    "إطلاق صاروخ باتجاه البلدة",
    "انفجار قنبلة قرب منزل",
    "تفجير مبنى في الخيام",
    "قذيفة سقطت في حولا",
    "قذائف مدفعية على كفركلا",
    "اغتيال شخص في غارة",
])
def test_rejects_strike_language(text: str) -> None:
    assert evaluate_air_violation_text(text).eligible is False


@pytest.mark.parametrize("text", [
    "سقوط شهيد في البلدة",
    "ثلاثة شهداء بعد الغارة",
    "استشهاد مواطن",
    "استشهد شخص متأثرا بجراحه",
    "سقوط جريح",
    "نقل عدد من الجرحى",
    "إصابة مواطن",
    "وقوع إصابات",
    "مقتل شخص وسقوط ضحايا",
    "نجاة فريق إسعاف من الغارة",
])
def test_rejects_casualty_language(text: str) -> None:
    assert evaluate_air_violation_text(text).eligible is False


@pytest.mark.parametrize("text", [
    "تدمير منزل في البلدة",
    "دمار كبير في المبنى",
    "وقوع أضرار مادية",
    "تضرر عدد من المنازل",
    "احتراق سيارة",
    "غارة تسببت في حريق",
    "قصف أدى إلى حريق منزل",
    "انفجار أدى إلى أضرار",
    "قذيفة سببت تدمير المبنى",
    "استهداف أدى إلى احتراق آلية",
])
def test_rejects_damage_language(text: str) -> None:
    assert evaluate_air_violation_text(text).eligible is False


def test_byline_casualty_title_is_not_an_event() -> None:
    result = evaluate_air_violation_text(
        "صفحة الإعلامي الشهيد علي شعيب:\nالطيران الحربي يحلق فوق بنت جبيل"
    )
    assert result.eligible is True


def test_empty_text_is_ineligible() -> None:
    result = evaluate_air_violation_text("  \n ")
    assert result.eligible is False
    assert result.reason == "empty_text"


def test_hashtags_urls_and_channel_handles_are_removed() -> None:
    result = evaluate_air_violation_text(
        "#الشهيد @channel https://example.test طيران استطلاعي فوق صور"
    )
    assert result.eligible is True


def test_hashtag_only_alert_keeps_its_tags_as_content() -> None:
    """Red Alert posts are nothing but hashtags, so they must not read empty."""
    result = evaluate_air_violation_text("#مقاتلات_حربية #الجنوب")
    assert result.eligible is True
    assert result.reason == "presence_only"


def test_hashtag_only_alert_still_rejects_kinetic_tags() -> None:
    result = evaluate_air_violation_text("#غارة #النبطية")
    assert result.eligible is False
    assert result.reason == "excluded_kinetic_casualty_or_damage"
