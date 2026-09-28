from datetime import date, time

from app.news.services.air_violations.window_grouping_service import (
    AirViolationWindowInput,
    group_air_violation_windows,
)


def _row(row_id: int, caza: str, day: date, event_time: time, condition_id: int = 36):
    return AirViolationWindowInput(
        id=row_id,
        condition_id=condition_id,
        caza_en=caza,
        caza_ar=None,
        event_date=day,
        event_time=event_time,
        villages=(f"Village {row_id}",),
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


def test_groups_warplane_reports_within_four_hours() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0), condition_id=35),
        _row(2, "Tyre", date(2026, 9, 17), time(13, 59), condition_id=35),
    ])

    assert len(windows) == 1
    assert windows[0].violation_count == 2


def test_splits_warplane_reports_after_four_hours() -> None:
    windows = group_air_violation_windows([
        _row(1, "Sour", date(2026, 9, 17), time(10, 0), condition_id=35),
        _row(2, "Tyre", date(2026, 9, 17), time(14, 1), condition_id=35),
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

