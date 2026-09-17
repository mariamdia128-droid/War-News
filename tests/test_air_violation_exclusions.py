from app.news.services.air_violations.air_violation_exclusions import air_violation_exclusion


def test_excludes_unifil_aircraft() -> None:
    result = air_violation_exclusion("تحليق طائرة تابعة لليونيفيل فوق الناقورة")

    assert result is not None
    assert result.reason == "excluded_unifil_aircraft"


def test_does_not_exclude_ocr_un_fragments() -> None:
    result = air_violation_exclusion("مسيرة فوق تبنين UN 6.43 UNP 6-40")

    assert result is None


def test_excludes_palestine_origin_route_without_concrete_violation() -> None:
    result = air_violation_exclusion("طيران حربي من فلسطين باتجاه جنوب لبنان")

    assert result is not None
    assert result.reason == "excluded_origin_route_palestine"


def test_keeps_palestine_origin_route_with_concrete_lebanese_violation() -> None:
    result = air_violation_exclusion(
        "طيران حربي من فلسطين باتجاه لبنان ثم تحليق فوق القطاع الغربي"
    )

    assert result is None
