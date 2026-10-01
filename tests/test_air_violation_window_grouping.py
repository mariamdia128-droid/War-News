from datetime import date, time

from app.news.services.air_violations.window_grouping_service import (
    AirViolationWindowInput,
    AirViolationWindowVillage,
    group_air_violation_windows,
)


def _row(
    row_id: int,
    caza: str,
    day: date,
    event_time: time,
    condition_id: int = 36,
    *,
    village_id: int | None = None,
    village_name: str | None = None,
):
    return AirViolationWindowInput(
        id=row_id,
        condition_id=condition_id,
        caza_en=caza,
        caza_ar=None,
        event_date=day,
        event_time=event_time,
        villages=(
            AirViolationWindowVillage(
                village_id=village_id if village_id is not None else row_id,
                name=village_name or f"Village {row_id}",
            ),
        ),
    )


def test_groups_reports_within_sixty_minutes() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0)),
        _row(2, "Tyre", date(2026, 9, 17), time(10, 59)),
    ])

    assert len(windows) == 1
    assert windows[0].violation_count == 2
    assert windows[0].caza_en == "Sour"


def test_splits_reports_over_sixty_minutes_from_anchor() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0)),
        _row(2, "Sour", date(2026, 9, 17), time(11, 1)),
    ])

    assert len(windows) == 2


def test_keeps_warplane_reports_independent_even_within_four_hours() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0), condition_id=35),
        _row(2, "Tyre", date(2026, 9, 17), time(13, 59), condition_id=35),
    ])

    assert len(windows) == 2
    assert all(window.violation_count == 1 for window in windows)


def test_splits_warplane_reports_after_four_hours() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0), condition_id=35),
        _row(2, "Tyre", date(2026, 9, 17), time(14, 1), condition_id=35),
    ])

    assert len(windows) == 2


def test_keeps_warplane_reports_with_identical_timestamps_independent() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0), condition_id=35),
        _row(2, "Tyre", date(2026, 9, 17), time(10, 0), condition_id=35),
    ])

    assert len(windows) == 2


def test_keeps_drone_and_warplane_windows_separate() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0), condition_id=35),
        _row(2, "Tyre", date(2026, 9, 17), time(10, 10), condition_id=36),
    ])

    assert len(windows) == 2


def test_groups_midnight_boundary() -> None:
    windows = group_air_violation_windows([
        _row(1, "Nabatieh", date(2026, 9, 17), time(23, 40)),
        _row(2, "Nabatiye", date(2026, 9, 18), time(0, 10)),
    ])

    assert len(windows) == 1
    assert windows[0].violation_count == 2


def test_keeps_cazas_separate() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0)),
        _row(2, "Saida", date(2026, 9, 17), time(10, 10)),
    ])

    assert len(windows) == 2


def test_groups_non_south_drone_reports_within_four_hours() -> None:
    windows = group_air_violation_windows([
        _row(1, "Koura", date(2026, 9, 17), time(10, 0)),
        _row(2, "Koura", date(2026, 9, 17), time(13, 59)),
    ])

    assert len(windows) == 1
    assert windows[0].violation_count == 2


def test_splits_non_south_drone_reports_after_four_hours() -> None:
    windows = group_air_violation_windows([
        _row(1, "Koura", date(2026, 9, 17), time(10, 0)),
        _row(2, "Koura", date(2026, 9, 17), time(14, 1)),
    ])

    assert len(windows) == 2


def test_keeps_helicopter_reports_independent() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0), condition_id=38),
        _row(2, "Tyre", date(2026, 9, 17), time(10, 1), condition_id=38),
    ])

    assert len(windows) == 2


def test_unconfirmed_surveillance_region_is_not_grouped() -> None:
    windows = group_air_violation_windows([
        _row(1, "South Lebanon", date(2026, 9, 17), time(10, 0)),
        _row(2, "South Lebanon", date(2026, 9, 17), time(10, 1)),
    ])

    assert len(windows) == 2


def test_requested_bekaa_and_baabda_cazas_use_one_hour_windows() -> None:
    for caza in ("Hermel", "Baalbek", "Baalbeck", "Baabda", "West Bekaa", "Hasbaiya"):
        windows = group_air_violation_windows([
            _row(1, caza, date(2026, 9, 17), time(10, 0)),
            _row(2, caza, date(2026, 9, 17), time(11, 1)),
        ])

        assert len(windows) == 2


def test_same_village_id_with_different_spellings_appears_once() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0), village_id=44, village_name="Tyre"),
        _row(2, "Sour", date(2026, 9, 17), time(10, 30), village_id=44, village_name="صور"),
    ])

    assert windows[0].violation_count == 2
    assert [(v.village_id, v.name) for v in windows[0].villages] == [(44, "Tyre")]


def test_different_ids_with_same_display_name_remain_distinct() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0), village_id=44, village_name="Abbassiyeh"),
        _row(2, "Sour", date(2026, 9, 17), time(10, 30), village_id=55, village_name="Abbassiyeh"),
    ])

    assert [v.village_id for v in windows[0].villages] == [44, 55]


def test_unresolved_name_dedupes_separately_from_resolved_id() -> None:
    rows = [
        AirViolationWindowInput(
            id=1,
            condition_id=36,
            caza_en="Sour",
            caza_ar=None,
            event_date=date(2026, 9, 17),
            event_time=time(10, 0),
            villages=(AirViolationWindowVillage(None, "  صور "),),
        ),
        AirViolationWindowInput(
            id=2,
            condition_id=36,
            caza_en="Sour",
            caza_ar=None,
            event_date=date(2026, 9, 17),
            event_time=time(10, 30),
            villages=(
                AirViolationWindowVillage(None, "صور"),
                AirViolationWindowVillage(44, "صور"),
            ),
        ),
    ]

    window = group_air_violation_windows(rows)[0]
    assert [(v.village_id, v.name.strip()) for v in window.villages] == [
        (None, "صور"),
        (44, "صور"),
    ]

