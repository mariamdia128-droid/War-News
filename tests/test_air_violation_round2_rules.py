"""Rules A, B, C, D and E -- the second-round air-violation decisions.

Each rule is tested in both directions: the text that must be rejected, and
the lookalike text that must still be accepted. The real posts that prompted
each rule are named in the docstrings so a future change can be traced back
to the row it was meant to fix.
"""

import pytest

from app.news.services.air_violations.air_violation_eligibility import (
    AirViolationOutcome,
    DENIAL_REASON,
    DENIAL_WITH_OVERFLIGHT_REASON,
    GENERIC_DIRECTION_REASON,
    NON_ISRAELI_REASON,
    UNMATCHED_LOCATION_REASON,
    evaluate_air_violation_location,
    evaluate_air_violation_text,
)


# --- Rule A: Israeli aircraft only ----------------------------------------


@pytest.mark.parametrize("text", [
    # The real row 1001. Note the spelling اليونيفل, one ي short of the
    # اليونيفيل the first round matched, which is why the row was created.
    "من تحليق مروحية تابعة للقوات الدولية اليونيفل فوق بلدة البازورية",
    "تحليق طائرة تابعة لليونيفيل فوق الناقورة",
    "مروحية تابعة لقوات الطوارئ الدولية تحلق فوق بلدة الخيام",
    "تحليق مروحية تابعة للأمم المتحدة فوق مرجعيون",
    "مروحية تابعة للصليب الأحمر تحلق فوق بلدة مجدل سلم",
    "تحليق طيران الجيش اللبناني فوق بلدة بريتال",
    "A UNIFIL helicopter was flying over Bazourieh",
])
def test_rule_a_rejects_non_israeli_aircraft(text: str) -> None:
    result = evaluate_air_violation_text(text)

    assert result.reason == NON_ISRAELI_REASON
    assert result.outcome is AirViolationOutcome.reject_no_incident
    assert result.belongs_in_incidents is False


@pytest.mark.parametrize("text", [
    # Israel is named as the operator, so the other party is only context.
    "الطيران الحربي الإسرائيلي يحلق فوق مقر اليونيفيل في بلدة الناقورة",
    "مسيرة إسرائيلية تحلق فوق مركز قوات الطوارئ الدولية في بلدة الناقورة",
    # A statement *by* the Lebanese army about Israeli aircraft.
    "أعلن الجيش اللبناني أن الطيران الحربي الإسرائيلي حلق فوق بلدة الخيام",
    # No party at all: the Red Alert default stays Israeli.
    "تحليق طيران حربي فوق بلدة عيترون",
])
def test_rule_a_keeps_israeli_and_unattributed_flights(text: str) -> None:
    assert evaluate_air_violation_text(text).eligible is True


def test_rule_a_needs_an_aircraft_word() -> None:
    """A UNIFIL patrol on the ground is not an air-violation question."""
    result = evaluate_air_violation_text("دورية تابعة لليونيفيل في بلدة الخيام")

    assert result.reason != NON_ISRAELI_REASON


# --- Rule B: denials and clarifications -----------------------------------


@pytest.mark.parametrize("text", [
    # The real row 1424, stored as Helicopter Hovering in Bint Jbeil.
    "حريق عادي في فرون لا يوجد غارة مروحية اقتضى التوضيح..",
    # The real row 1535, stored as Warplane in Baalbek.
    "#تنويه الطيران المسموع في أجواء البقاع – بعلبك والجوار هو طيران مدني ،"
    " بعد تحويل مسار الرحلات لأسباب روتينية وطبيعية،"
    " ولا يوجد أي طيران حربي في الأجواء.",
    "لا صحة لخبر تحليق المسيرات فوق بلدة عيتا الشعب",
    "نفي تحليق طيران حربي فوق مدينة صور",
    "ما تم تداوله عن غارة في بلدة حولا خبر غير صحيح",
    "شائعة تحليق مروحية فوق بلدة يارون",
])
def test_rule_b_rejects_denials_and_clarifications(text: str) -> None:
    result = evaluate_air_violation_text(text)

    assert result.reason == DENIAL_REASON
    assert result.outcome is AirViolationOutcome.reject_no_incident
    assert result.belongs_in_incidents is False


def test_rule_b_denial_plus_a_real_overflight_is_held_not_rejected() -> None:
    """Two claims in one post: the deterministic rule cannot pick one."""
    result = evaluate_air_violation_text(
        "لا صحة لخبر الغارة على عيترون، لكن الطيران الحربي الإسرائيلي"
        " يحلق فوق بلدة عيترون"
    )

    assert result.reason == DENIAL_WITH_OVERFLIGHT_REASON
    assert result.outcome is AirViolationOutcome.hold_for_review
    assert result.belongs_in_incidents is False


@pytest.mark.parametrize("text", [
    # The negation does not reach the aircraft: a real overflight, plus a
    # separate statement that something else is absent.
    "تحليق طيران حربي فوق بلدة الخيام ولا يوجد تيار كهربائي في البلدة",
    "مسيرة تحلق فوق بلدة كفركلا، لا يوجد ماء في البلدة منذ أسبوع",
])
def test_rule_b_negation_must_negate_the_aircraft(text: str) -> None:
    assert evaluate_air_violation_text(text).eligible is True


# --- Rule D: generic country-level direction ------------------------------


@pytest.mark.parametrize("text", [
    # The real row 1531 (t.me/redlinkleb/45981) and its repeat, row 1586.
    "🔴\n✈️\n#مقاتلات_حربية\n#لبنان\nاتجاه لبنان\nالخريطة المباشرة\n<O>",
    "🔴\n✈️\n#مقاتلات_حربية\n#لبنان\nاتجاه اتجاه لبنان\nالخريطة المباشرة\n<O>",
    "#مقاتلات_حربية #لبنان باتجاه لبنان الخريطة المباشرة",
    "طيران حربي نحو لبنان الخريطة المباشرة",
    # The row admits it has no location.
    "طيران استطلاعي - الموقع بحاجة إلى التحقق",
])
def test_rule_d_rejects_country_level_direction(text: str) -> None:
    result = evaluate_air_violation_text(text)

    assert result.reason == GENERIC_DIRECTION_REASON
    assert result.outcome is AirViolationOutcome.reject_no_incident
    assert result.belongs_in_incidents is False


@pytest.mark.parametrize("text", [
    # A named region is a location, and the tag is the only place it appears,
    # so the location test must read hashtags even though the event text does
    # not. These are the legitimate regional Warplane alerts.
    "طيران حربي — #الجنوب  الخريطة المباشرة <O>",
    "طيران حربي — #البقاع  الخريطة المباشرة <O>",
    "تحليق #مقاتلات_حربية #الجنوب #أقصى_درجات_الحذر الخريطة المباشرة <O>",
    "طيران حربي فوق القطاع الغربي والقطاع الشرقي",
    "تحليق مسيرة فوق بلدة عيترون الخريطة المباشرة",
])
def test_rule_d_keeps_rows_that_name_a_region_or_a_place(text: str) -> None:
    assert evaluate_air_violation_text(text).eligible is True


def test_rule_d_does_not_outrank_a_strike_report() -> None:
    """A strike with no location is still an incident, not a rejected row."""
    result = evaluate_air_violation_text("غارة إسرائيلية باتجاه لبنان")

    assert result.belongs_in_incidents is True


# --- Whole-token matching -------------------------------------------------


@pytest.mark.parametrize("text", [
    # غاره inside المغارة was the first-round false positive. The rules added
    # here match whole tokens, so no new rule may reintroduce it.
    "طيران استطلاعي فوق نهر المغارة",
    "مسيرة تحلق فوق المغارة في قضاء الشوف",
    # عدو inside a village name must not read as Israeli attribution, and
    # must not satisfy rule A's escape hatch for a UNIFIL flight.
    "مسيرة تحلق فوق بلدة عدشيت",
    # Latin "unifil" must not be found inside an unrelated OCR fragment.
    "مسيرة فوق تبنين UN 6.43 UNP 6-40",
])
def test_new_rules_match_tokens_not_substrings(text: str) -> None:
    assert evaluate_air_violation_text(text).eligible is True


@pytest.mark.parametrize("text", [
    "تحليق مروحية تابعة لليونيفيل فوق بلدة الخيام",
    "تحليق مروحية تابعة للقوات الدولية اليونيفل فوق بلدة الخيام",
    "تحليق مروحية اليونيفيل فوق بلدة الخيام",
])
def test_clitic_prefixes_still_match(text: str) -> None:
    """ال and the و/ف/ب/ك/ل prepositions attach to the noun in Arabic."""
    assert evaluate_air_violation_text(text).reason == NON_ISRAELI_REASON


# --- Rules C and E: a named location is required --------------------------


def test_rule_c_a_resolved_village_always_passes() -> None:
    result = evaluate_air_violation_location(
        "تحليق مسيرة فوق بلدة عيترون", has_resolved_village=True
    )

    assert result.eligible is True


@pytest.mark.parametrize("caza_label", ["Multiple regions", "South Lebanon", "Sour"])
def test_rule_c_a_recognised_region_stands_in_for_a_village(caza_label: str) -> None:
    """Legitimate multi-region Warplane rows must keep working."""
    result = evaluate_air_violation_location(
        "طيران حربي فوق القطاع الغربي والقطاع الشرقي",
        has_resolved_village=False,
        caza_label=caza_label,
    )

    assert result.eligible is True


def test_rule_c_region_named_only_in_a_hashtag_passes() -> None:
    result = evaluate_air_violation_location(
        "طيران حربي — #الجنوب  الخريطة المباشرة <O>", has_resolved_village=False
    )

    assert result.eligible is True


def test_rule_d_beats_the_caza_fallback() -> None:
    """Bare لبنان maps to "Multiple regions" upstream; that is bug 3.

    Rule D must be decided before the caza label is trusted, or row 1531
    would be accepted all over again.
    """
    result = evaluate_air_violation_location(
        "#مقاتلات_حربية #لبنان اتجاه لبنان الخريطة المباشرة <O>",
        has_resolved_village=False,
        caza_label="Multiple regions",
    )

    assert result.reason == GENERIC_DIRECTION_REASON
    assert result.outcome is AirViolationOutcome.reject_no_incident


def test_rule_e_records_the_unmatched_name_for_review() -> None:
    result = evaluate_air_violation_location(
        "تحليق مسيرة فوق بلدة كفرشلالا", has_resolved_village=False
    )

    assert result.reason == UNMATCHED_LOCATION_REASON
    assert result.outcome is AirViolationOutcome.hold_for_review
    assert result.unmatched_location == "كفرشلالا"
    assert result.belongs_in_incidents is False


def test_rule_e_prefers_the_extractor_name_when_one_is_given() -> None:
    result = evaluate_air_violation_location(
        "تحليق مسيرة فوق بلدة البازورية",
        has_resolved_village=False,
        unmatched_names=("البازورية",),
    )

    assert result.reason == UNMATCHED_LOCATION_REASON
    assert result.unmatched_location == "البازورية"


def test_no_rejected_outcome_can_reach_the_incident_pipeline() -> None:
    """The whole point of the outcome split: reject means reject."""
    for text in (
        "من تحليق مروحية تابعة للقوات الدولية اليونيفل فوق بلدة البازورية",
        "حريق عادي في فرون لا يوجد غارة مروحية اقتضى التوضيح..",
        "🔴 #مقاتلات_حربية #لبنان اتجاه لبنان الخريطة المباشرة <O>",
    ):
        result = evaluate_air_violation_text(text)
        assert result.outcome is AirViolationOutcome.reject_no_incident
        assert result.belongs_in_incidents is False
        assert result.rejected_without_incident is True
