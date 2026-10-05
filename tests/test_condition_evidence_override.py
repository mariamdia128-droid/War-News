from app.news.services.matching.condition_evidence_override import (
    apply_condition_evidence_override,
    condition_fallback_from_text,
)


def test_tank_firing_at_village_overrides_artillery() -> None:
    text = "قصف تنفذه دبابة ميركافا يستهدف أحياء زوطر الشرقية"
    assert apply_condition_evidence_override(text, "Artillery Shelling") == "Tank Fire"


def test_tank_that_targets_village_overrides_artillery() -> None:
    text = "دبابة ميركافا معادية متمركزة في البياضة تستهدف بلدة المنصوري بالقذائف"
    assert apply_condition_evidence_override(text, "Artillery Shelling") == "Tank Fire"


def test_tank_mentioned_as_target_does_not_override() -> None:
    text = "استهدفنا بصاروخ موجه دبابة ميركافا وحققنا إصابة مباشرة"
    assert apply_condition_evidence_override(text, "Bombs") == "Bombs"


def test_tank_incursion_does_not_become_tank_fire() -> None:
    text = "توغل دبابتين ميركافا باتجاه المنطقة مع إطلاق رشقات رشاشة"
    assert apply_condition_evidence_override(text, "Ground Incursion") == "Ground Incursion"


def test_warplane_airstrike_becomes_bombs() -> None:
    text = "الطيران الحربي الإسرائيلي أغار مستهدفًا بلدة المنصوري"
    assert apply_condition_evidence_override(text, "Warplane") == "Bombs"


def test_warplane_overflight_remains_air_activity() -> None:
    text = "تحليق طيران حربي فوق الجنوب"
    assert apply_condition_evidence_override(text, "Warplane") == "Warplane"


def test_warning_and_feigned_raids_keep_specific_conditions() -> None:
    assert apply_condition_evidence_override("غارة تحذيرية", "Bombs") == "Warning Raid"
    assert apply_condition_evidence_override("غارات وهمية", "Bombs") == "Feigned Attacks"


def test_drone_strike_maps_to_bombs() -> None:
    assert condition_fallback_from_text("غارة من مسيرة على سيارة") == "Bombs"
    assert condition_fallback_from_text("استهدفت مسيرة آلية") == "Bombs"


def test_explosive_drone_maps_to_suicide_drone() -> None:
    assert condition_fallback_from_text("مسيرة مفخخة فوق البلدة") == "Suicide Drone"


def test_crashed_drone_maps_to_drone_failure() -> None:
    assert condition_fallback_from_text("سقوط مسيرة في خراج البلدة") == "Drone Failure"


def test_presence_only_drone_maps_to_surveillance_aircraft() -> None:
    assert condition_fallback_from_text("تحليق مسيرة فوق البلدة") == "Surveillance Aircraft"
    assert condition_fallback_from_text("طيران مسير في الأجواء") == "Surveillance Aircraft"


def test_bare_drone_without_context_does_not_fallback_to_air_activity() -> None:
    assert condition_fallback_from_text("مسيرة") is None
