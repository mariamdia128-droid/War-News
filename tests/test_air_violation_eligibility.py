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
    "أغار الطيران الحربي على البلدة",
    "غارتان استهدفتا منزلا",
    "airstrike attacked a building",
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
    assert result.reason == "excluded_hashtag_only_ambiguous"


@pytest.mark.parametrize("text", ["#الشهيد", "#شهداء #لبنان", "#غارة #النبطية"])
def test_bare_tags_are_never_read_as_an_incident(text: str) -> None:
    """A tag labels a feed; it reports nothing, so a human decides."""
    result = evaluate_air_violation_text(text)
    assert result.eligible is False
    assert result.reason == "excluded_hashtag_only_ambiguous"
    assert result.belongs_in_incidents is False


@pytest.mark.parametrize("text", [
    "🤍 منذ 20 تشرين الثاني 2025، وأنتم جزء من هذه المسيرة بدأنا بمجموعة لا تتجاوز 20 فردًا"
    " كل من ارسل بلاغا عن طائرة مسيرة، او حربي، او غارة، او اي حدث ميداني",
    "إحصاءات نهاية اليوم · الأحد ٢٣ آب ٢٠٢٦ إجمالي التنبيهات: ١٤٨ غارات جوية: ٧ قصف مدفعي: ٣٧",
    "أكثر القرى رصداً (مسيّرات): النبطية الفوقا — رُصدت ٢١",
])
def test_non_event_notices_are_not_incidents(text: str) -> None:
    """Digests and channel notices list kinetic words without reporting one."""
    result = evaluate_air_violation_text(text)
    assert result.eligible is False
    assert result.reason == "excluded_non_event_notice"
    assert result.belongs_in_incidents is False


@pytest.mark.parametrize("text", [
    "طيران استطلاعي فوق نهر المغارة",
    "مسيرة تحلق فوق المغارة في قضاء الشوف",
])
def test_place_names_that_merely_contain_a_strike_word_are_not_strikes(text: str) -> None:
    """المغارة is a cave, not a غارة."""
    assert evaluate_air_violation_text(text).eligible is True


def test_a_real_strike_near_that_place_is_still_a_strike() -> None:
    result = evaluate_air_violation_text("غارة إسرائيلية على نهر المغارة")
    assert result.eligible is False
    assert result.belongs_in_incidents is True


def test_a_real_strike_still_belongs_in_incidents() -> None:
    result = evaluate_air_violation_text("أغار الطيران الحربي مستهدفا بلدة المنصوري")
    assert result.belongs_in_incidents is True
