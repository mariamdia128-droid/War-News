from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable

from app.news.constants.air_violation_conditions import (
    AIR_VIOLATION_DRONE_CONDITION_ID,
    AIR_VIOLATION_SOUTH_CAZAS,
)
from app.news.services.air_violations.caza_alias_resolver import canonicalize_caza
from app.core.text_normalization import normalize_arabic_text

DRONE_SOUTH_WINDOW_LENGTH = timedelta(minutes=60)
STANDARD_WINDOW_LENGTH = timedelta(hours=4)
UNGROUPED_SURVEILLANCE_CAZAS = frozenset({"Multiple regions", "South Lebanon", "Unknown"})


@dataclass(frozen=True)
class AirViolationWindowVillage:
    village_id: int | None
    name: str


@dataclass(frozen=True)
class AirViolationWindowInput:
    id: int
    condition_id: int
    caza_en: str | None
    caza_ar: str | None
    event_date: date
    event_time: time | None
    villages: tuple[AirViolationWindowVillage, ...] = ()


@dataclass(frozen=True)
class AirViolationWindow:
    id: str
    caza_en: str
    caza_ar: str | None
    window_start: datetime
    window_end: datetime
    violation_count: int
    villages: tuple[AirViolationWindowVillage, ...]


def _event_datetime(row: AirViolationWindowInput) -> datetime:
    return datetime.combine(row.event_date, row.event_time or time.min)


def group_air_violation_windows(
    rows: Iterable[AirViolationWindowInput],
) -> list[AirViolationWindow]:
    partitions: dict[tuple[str, int], list[AirViolationWindowInput]] = {}
    caza_ar_by_key: dict[str, str | None] = {}
    for row in rows:
        caza = canonicalize_caza(row.caza_en) or canonicalize_caza(row.caza_ar)
        if not caza:
            caza = "Unknown"
        partitions.setdefault((caza, row.condition_id), []).append(row)
        caza_ar_by_key.setdefault(caza, row.caza_ar)

    windows: list[AirViolationWindow] = []
    for (caza, condition_id), items in partitions.items():
        if not _uses_surveillance_window(condition_id, caza):
            for item in items:
                item_dt = _event_datetime(item)
                windows.append(_build_window(caza, caza_ar_by_key.get(caza), condition_id, [item], item_dt))
            continue
        window_length = _window_length_for_condition(condition_id, caza)
        ordered = sorted(items, key=lambda item: (_event_datetime(item), item.id))
        current: list[AirViolationWindowInput] = []
        anchor: datetime | None = None
        for item in ordered:
            item_dt = _event_datetime(item)
            if anchor is None or item_dt - anchor > window_length:
                if current and anchor is not None:
                    windows.append(_build_window(caza, caza_ar_by_key.get(caza), condition_id, current, anchor))
                current = [item]
                anchor = item_dt
            else:
                current.append(item)
        if current and anchor is not None:
            windows.append(_build_window(caza, caza_ar_by_key.get(caza), condition_id, current, anchor))

    return sorted(windows, key=lambda item: (item.window_start, item.caza_en), reverse=True)


def assign_air_violation_window_ids(
    rows: Iterable[AirViolationWindowInput],
) -> dict[int, str]:
    assignments: dict[int, str] = {}
    partitions: dict[tuple[str, int], list[AirViolationWindowInput]] = {}
    for row in rows:
        caza = canonicalize_caza(row.caza_en) or canonicalize_caza(row.caza_ar)
        if not caza:
            continue
        partitions.setdefault((caza, row.condition_id), []).append(row)

    for (caza, condition_id), items in partitions.items():
        if not _uses_surveillance_window(condition_id, caza):
            for item in items:
                item_dt = _event_datetime(item)
                assignments[item.id] = f"{condition_id}:{caza}:{item_dt.isoformat()}:{item.id}"
            continue
        window_length = _window_length_for_condition(condition_id, caza)
        ordered = sorted(items, key=lambda item: (_event_datetime(item), item.id))
        anchor: datetime | None = None
        current_window_id: str | None = None
        for item in ordered:
            item_dt = _event_datetime(item)
            if anchor is None or item_dt - anchor > window_length:
                anchor = item_dt
                current_window_id = f"{condition_id}:{caza}:{anchor.isoformat()}"
            if current_window_id is not None:
                assignments[item.id] = current_window_id
    return assignments


def _window_length_for_condition(condition_id: int, caza_en: str | None = None) -> timedelta:
    if condition_id != AIR_VIOLATION_DRONE_CONDITION_ID:
        # Warplanes and helicopters are event records, not surveillance windows.
        return timedelta(0)
    if (
        condition_id == AIR_VIOLATION_DRONE_CONDITION_ID
        and canonicalize_caza(caza_en) in AIR_VIOLATION_SOUTH_CAZAS
    ):
        return DRONE_SOUTH_WINDOW_LENGTH
    return STANDARD_WINDOW_LENGTH


def surveillance_window_minutes(caza_en: str | None) -> int | None:
    """Return the configured window for a confirmed caza, otherwise no window."""
    caza = canonicalize_caza(caza_en)
    if not caza or caza in UNGROUPED_SURVEILLANCE_CAZAS:
        return None
    return int(_window_length_for_condition(AIR_VIOLATION_DRONE_CONDITION_ID, caza).total_seconds() // 60)


def _uses_surveillance_window(condition_id: int, caza_en: str | None) -> bool:
    return condition_id == AIR_VIOLATION_DRONE_CONDITION_ID and surveillance_window_minutes(caza_en) is not None


def _build_window(
    caza: str,
    caza_ar: str | None,
    condition_id: int,
    items: list[AirViolationWindowInput],
    anchor: datetime,
) -> AirViolationWindow:
    end = max(_event_datetime(item) for item in items)
    # Inputs are chronological, so first insertion is the earliest report for
    # that village. IDs are authoritative; unresolved names occupy a separate
    # namespace and can never collapse with a resolved ID.
    villages_by_key: dict[tuple[str, object], AirViolationWindowVillage] = {}
    for item in sorted(items, key=lambda row: (_event_datetime(row), row.id)):
        for village in item.villages:
            normalized_name = " ".join(
                normalize_arabic_text(village.name).casefold().split()
            )
            key = (
                ("id", village.village_id)
                if village.village_id is not None
                else ("name", normalized_name)
            )
            if normalized_name:
                villages_by_key.setdefault(key, village)
    villages = tuple(villages_by_key.values())
    return AirViolationWindow(
        id=f"{condition_id}:{caza}:{anchor.isoformat()}",
        caza_en=caza,
        caza_ar=caza_ar,
        window_start=anchor,
        window_end=end,
        violation_count=len(items),
        villages=villages,
    )
