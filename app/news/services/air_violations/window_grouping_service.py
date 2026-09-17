from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable

from app.news.services.air_violations.caza_alias_resolver import canonicalize_caza

WINDOW_LENGTH = timedelta(minutes=60)


@dataclass(frozen=True)
class AirViolationWindowInput:
    id: int
    caza_en: str | None
    caza_ar: str | None
    event_date: date
    event_time: time | None
    villages: tuple[str, ...] = ()


@dataclass(frozen=True)
class AirViolationWindow:
    id: str
    caza_en: str
    caza_ar: str | None
    window_start: datetime
    window_end: datetime
    violation_count: int
    villages: tuple[str, ...]


def _event_datetime(row: AirViolationWindowInput) -> datetime:
    return datetime.combine(row.event_date, row.event_time or time.min)


def group_air_violation_windows(
    rows: Iterable[AirViolationWindowInput],
) -> list[AirViolationWindow]:
    partitions: dict[str, list[AirViolationWindowInput]] = {}
    caza_ar_by_key: dict[str, str | None] = {}
    for row in rows:
        caza = canonicalize_caza(row.caza_en) or canonicalize_caza(row.caza_ar)
        if not caza:
            caza = "Unknown"
        partitions.setdefault(caza, []).append(row)
        caza_ar_by_key.setdefault(caza, row.caza_ar)

    windows: list[AirViolationWindow] = []
    for caza, items in partitions.items():
        ordered = sorted(items, key=lambda item: (_event_datetime(item), item.id))
        current: list[AirViolationWindowInput] = []
        anchor: datetime | None = None
        for item in ordered:
            item_dt = _event_datetime(item)
            if anchor is None or item_dt - anchor > WINDOW_LENGTH:
                if current and anchor is not None:
                    windows.append(_build_window(caza, caza_ar_by_key.get(caza), current, anchor))
                current = [item]
                anchor = item_dt
            else:
                current.append(item)
        if current and anchor is not None:
            windows.append(_build_window(caza, caza_ar_by_key.get(caza), current, anchor))

    return sorted(windows, key=lambda item: (item.window_start, item.caza_en), reverse=True)


def assign_air_violation_window_ids(
    rows: Iterable[AirViolationWindowInput],
) -> dict[int, str]:
    assignments: dict[int, str] = {}
    partitions: dict[str, list[AirViolationWindowInput]] = {}
    for row in rows:
        caza = canonicalize_caza(row.caza_en) or canonicalize_caza(row.caza_ar)
        if not caza:
            continue
        partitions.setdefault(caza, []).append(row)

    for caza, items in partitions.items():
        ordered = sorted(items, key=lambda item: (_event_datetime(item), item.id))
        anchor: datetime | None = None
        current_window_id: str | None = None
        for item in ordered:
            item_dt = _event_datetime(item)
            if anchor is None or item_dt - anchor > WINDOW_LENGTH:
                anchor = item_dt
                current_window_id = f"{caza}:{anchor.isoformat()}"
            if current_window_id is not None:
                assignments[item.id] = current_window_id
    return assignments


def _build_window(
    caza: str,
    caza_ar: str | None,
    items: list[AirViolationWindowInput],
    anchor: datetime,
) -> AirViolationWindow:
    end = max(_event_datetime(item) for item in items)
    villages = tuple(
        dict.fromkeys(
            village
            for item in items
            for village in item.villages
            if village
        )
    )
    return AirViolationWindow(
        id=f"{caza}:{anchor.isoformat()}",
        caza_en=caza,
        caza_ar=caza_ar,
        window_start=anchor,
        window_end=end,
        violation_count=len(items),
        villages=villages,
    )
