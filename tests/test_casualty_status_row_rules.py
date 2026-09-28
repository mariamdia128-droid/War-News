import pytest

from app.news.services.incident_details.casualty_status import status_for_incident_row
from app.news.services.incident_details.casualty_text import find_count_mentions


def _match(*entries):
    return {"village_matches": list(entries)}


def _role(village, village_id, *, status="matched", deaths=None, injuries=None):
    return {
        "village": village,
        "village_role": "target",
        "village_match_status": status,
        "matched_village_id": village_id,
        "deaths": deaths,
        "injuries": injuries,
    }


def _derive(text, extraction, village_id, match_result, target_count):
    return status_for_incident_row(
        text,
        extraction,
        {"deaths": 99, "injuries": 99},
        row_village_id=village_id,
        match_result=match_result,
        target_location_count=target_count,
    )


def test_32767_reihan_death_is_exact_and_injuries_are_not_stated() -> None:
    extraction = {
        "casualties": {"total_deaths": 1, "total_injuries": 10},
        "village_roles": [
            {"village": "الريحان", "deaths": 1},
            {"village": "حي المسلخ", "injuries": 9},
            {"village": "النبطية الفوقا", "injuries": 1},
        ],
    }
    result = _derive(
        "شهيد في الريحان و9 جرحى في حي المسلخ وجريح في النبطية الفوقا",
        extraction,
        1316,
        _match(
            _role("الريحان", 1316, deaths=1),
            _role("حي المسلخ", 543, status="low_confidence", injuries=9),
            _role("النبطية الفوقا", 1153, injuries=1),
        ),
        3,
    )
    assert result.deaths_status == "exact"
    assert result.injuries_status == "none_mentioned"


def test_32756_dawer_does_not_inherit_stored_counts() -> None:
    extraction = {
        "casualties": {"total_deaths": 1, "total_injuries": 10},
        "village_roles": [
            {"village": "الريحان", "deaths": 1},
            {"village": "حي المسلخ", "injuries": 9},
            {"village": "النبطية الفوقا", "injuries": 1},
        ],
    }
    result = _derive(
        "شهيد في الريحان و9 جرحى في حي المسلخ وجريح في النبطية الفوقا",
        extraction,
        543,
        _match(
            _role("الريحان", 48, status="low_confidence", deaths=1),
            _role("حي المسلخ", 543, status="low_confidence", injuries=9),
            _role("النبطية الفوقا", 1153, injuries=1),
        ),
        3,
    )
    assert result.deaths_status == "none_mentioned"
    assert result.injuries_status == "none_mentioned"


@pytest.mark.parametrize("message_id,targets,deaths,injuries", [
    (32072, 3, 5, 24),
    (32095, 5, 3, 23),
    (31863, 4, 4, 32),
])
def test_real_aggregate_bulletins_stay_unallocated(message_id, targets, deaths, injuries) -> None:
    result = _derive(
        f"حصيلة الغارات اليوم: {deaths} شهداء و{injuries} جريحاً",
        {"casualties": {"total_deaths": deaths, "total_injuries": injuries}},
        1000 + message_id,
        _match(),
        targets,
    )
    assert result.deaths_status == result.injuries_status == "aggregate_only"
    assert result.remaining_total == {"deaths": deaths, "injuries": injuries}


def test_32735_has_unallocated_injury_total_but_no_death_for_unmatched_row() -> None:
    result = _derive(
        "شهيد في الريحان و10 جرحى في النبطية",
        {
            "casualties": {"total_deaths": 1, "total_injuries": 10},
            "village_roles": [{"village": "الريحان", "deaths": 1}],
        },
        48,
        _match(_role("الريحان", 48, status="low_confidence", deaths=1)),
        3,
    )
    assert result.deaths_status == "none_mentioned"
    assert result.injuries_status == "aggregate_only"


def test_per_location_sum_below_total_retains_only_remainder() -> None:
    result = _derive(
        "الحصيلة 5 شهداء: شهيدان في ألف وشهيد في باء",
        {
            "casualties": {"total_deaths": 5},
            "village_roles": [
                {"village": "ألف", "deaths": 2},
                {"village": "باء", "deaths": 1},
            ],
        },
        3,
        _match(_role("ألف", 1, deaths=2), _role("باء", 2, deaths=1), _role("جيم", 3)),
        3,
    )
    assert result.deaths_status == "aggregate_only"
    assert result.remaining_total == {"deaths": 2}


def test_31955_current_named_victim_is_one_exact_death() -> None:
    result = _derive(
        "ارتقى الشهيد علي حسن اليوم إثر الغارة على جويا",
        {"casualties": {}, "village_roles": [{"village": "جويا"}]},
        768,
        _match(_role("جويا", 768)),
        1,
    )
    assert result.deaths_status == "exact"
    assert result.injuries_status == "none_mentioned"


@pytest.mark.parametrize("text", [
    "استشهد الشهـ.. علي حسن اليوم إثر الغارة",
    "ارتقت شهيـ فاطمة حسن صباح اليوم إثر الغارة",
])
def test_current_censored_named_victim_is_normalized_and_exact(text) -> None:
    assert any(item.kind == "deaths" and item.value == 1 for item in find_count_mentions(text))
    result = _derive(text, {"casualties": {}}, 10, _match(_role("جويا", 10)), 1)
    assert result.deaths_status == "exact"


@pytest.mark.parametrize("message_id", [31831, 31824])
def test_older_obituary_stays_unmentioned_even_with_stored_counts(message_id) -> None:
    result = _derive(
        f"ينعى أهالي البلدة الشهيد علي حسن الذي استشهد في غارة سابقة ({message_id})",
        {"casualties": {}},
        message_id,
        _match(_role("البلدة", message_id)),
        1,
    )
    assert result.deaths_status == result.injuries_status == "none_mentioned"
