"""Deterministic per-message casualty status derivation.

This module never calls an LLM or accesses a database. It combines the source
wording with the final extracted counts. For a multi-location bulletin, a
known per-location count remains visible while ``remaining_total`` records any
unallocated remainder from a larger bulletin total.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from app.llm.dtos import ExtractionCasualties
from app.news.services.incident_details.casualty_text import (
    DEATHS,
    INJURIES,
    find_count_mentions,
    find_explicit_none,
    has_casualty_wording,
    has_explicit_none,
    has_vague_quantifier,
    is_obituary,
    mentions_named_victim,
    normalize_casualty_text,
    sentences,
    strip_page_header,
)

CasualtyStatusCode = Literal[
    "none_mentioned",
    "explicit_none",
    "exact",
    "count_missing",
    "aggregate_only",
]

_STATUS_PRIORITY = {
    "none_mentioned": 0,
    "explicit_none": 1,
    "exact": 2,
    "count_missing": 3,
    "aggregate_only": 4,
}
_PRELIMINARY_PATTERNS = tuple(
    re.compile(normalize_casualty_text(pattern))
    for pattern in (
        r"حصيلة\s+(?:أولية|مؤقتة|غير\s+نهائية)",
        r"(?:المعلومات|معلومات)\s+الأولية\s+عن\s+(?:سقوط|استشهاد|إصابة)",
        r"(?:ارتفاع|ارتفع)\s+(?:عدد|حصيلة)",
        r"(?:تحديث|مراجعة|تصحيح)\s+(?:في\s+)?الحصيلة",
    )
)
_FINAL_TOLL = re.compile(normalize_casualty_text(r"حصيلة\s+نهائية"))


@dataclass(frozen=True)
class CasualtyStatusResult:
    status: CasualtyStatusCode
    deaths_status: CasualtyStatusCode
    injuries_status: CasualtyStatusCode
    is_preliminary: bool
    evidence: str | None
    remaining_total: dict[str, int]


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _positive_counts(value: Any, kind: str) -> list[int]:
    fields = (
        kind,
        f"total_{kind}",
        f"male_{kind}",
        f"female_{kind}",
        f"children_{kind}",
    )
    values = []
    for field in fields:
        count = _get(value, field)
        if isinstance(count, int) and not isinstance(count, bool) and count > 0:
            values.append(count)
    return values


def _locations_with_counts(
    village_roles: Any,
    sub_events: Any,
    kind: str,
) -> list[tuple[str, int]]:
    per_location: dict[str, int] = {}
    for role in village_roles or ():
        if _get(role, "role", "target") not in ("target", getattr(_get(role, "role"), "value", None)):
            continue
        name = str(_get(role, "village", "")).strip()
        count = _get(role, kind)
        if name and isinstance(count, int) and not isinstance(count, bool) and count > 0:
            per_location[name] = max(per_location.get(name, 0), count)

    for event in sub_events or ():
        locations = _get(event, "locations", ()) or ()
        event_counts = _positive_counts(_get(event, "casualties"), kind)
        event_total = _get(_get(event, "casualties"), kind)
        if len(locations) == 1 and isinstance(event_total, int) and event_total > 0:
            loc = locations[0]
            if _get(loc, "role", "target") in ("target", getattr(_get(loc, "role"), "value", None)):
                name = str(_get(loc, "village", "")).strip()
                if name:
                    per_location[name] = max(per_location.get(name, 0), event_total)
        for loc in locations:
            if _get(loc, "role", "target") not in ("target", getattr(_get(loc, "role"), "value", None)):
                continue
            name = str(_get(loc, "village", "")).strip()
            count = _get(loc, kind)
            if name and isinstance(count, int) and not isinstance(count, bool) and count > 0:
                per_location[name] = max(per_location.get(name, 0), count)
        # A sub-event total with several targets is an aggregate, not a village row.
        if len(locations) > 1 and event_counts:
            continue
    return list(per_location.items())


def _has_explicit_count(text: str, kind: str) -> bool:
    return any(mention.kind == kind and mention.value > 0 for mention in find_count_mentions(text))


def _is_preliminary(text: str) -> bool:
    cleaned = strip_page_header(text)
    for sentence in sentences(cleaned):
        normalized = normalize_casualty_text(sentence)
        if _FINAL_TOLL.search(normalized):
            continue
        if not (
            has_casualty_wording(sentence, DEATHS)
            or has_casualty_wording(sentence, INJURIES)
        ):
            continue
        if any(pattern.search(normalized) for pattern in _PRELIMINARY_PATTERNS):
            return True
    return False


def _status_for_kind(
    text: str,
    kind: str,
    casualties: Any,
    village_roles: Any,
    sub_events: Any,
    target_location_count: int,
) -> tuple[CasualtyStatusCode, int | None, str | None]:
    if is_obituary(text):
        return "none_mentioned", None, None

    located = _locations_with_counts(village_roles, sub_events, kind)
    root_values = _positive_counts(casualties, kind)
    root_direct = _get(casualties, kind)
    root_total = _get(casualties, f"total_{kind}")
    if located:
        total = root_total if isinstance(root_total, int) and root_total > 0 else None
        if total is None:
            mentions = [
                mention.value
                for mention in find_count_mentions(text)
                if mention.kind == kind and mention.counts_total and mention.value > 0
            ]
            total = max(mentions, default=None)
        located_sum = sum(count for _, count in located)
        if total is not None and total > located_sum:
            return "aggregate_only", total - located_sum, _evidence(text, kind)
        return "exact", None, _evidence(text, kind)

    if target_location_count == 1 and root_values:
        return "exact", None, _evidence(text, kind)

    if target_location_count >= 2:
        aggregate = root_total if isinstance(root_total, int) and root_total > 0 else None
        if aggregate is None and isinstance(root_direct, int) and root_direct > 0:
            aggregate = root_direct
        if aggregate is None:
            mentions = [
                mention.value
                for mention in find_count_mentions(text)
                if mention.kind == kind and mention.counts_total and mention.value > 0
            ]
            aggregate = max(mentions, default=None)
        if aggregate is not None:
            return "aggregate_only", aggregate, _evidence(text, kind)

    if _has_explicit_count(text, kind) and target_location_count == 1:
        # The text has an exact toll, but the extraction did not persist it.
        return "count_missing", None, _evidence(text, kind)

    if has_explicit_none(text, kind):
        return "explicit_none", None, find_explicit_none(text, kind)

    has_wording = has_casualty_wording(text, kind) or has_vague_quantifier(text, kind)
    if mentions_named_victim(text):
        has_wording = False
    if has_wording:
        return "count_missing", None, _evidence(text, kind)
    return "none_mentioned", None, None


def _evidence(text: str, kind: str) -> str | None:
    cleaned = strip_page_header(text)
    for sentence in sentences(cleaned):
        if has_casualty_wording(sentence, kind) or has_vague_quantifier(sentence, kind):
            return sentence.strip()[:320]
    return None


def derive_casualty_status(
    message_text: str,
    casualties: ExtractionCasualties | dict[str, Any] | None,
    *,
    village_roles: Any = (),
    sub_events: Any = (),
    target_location_count: int,
) -> CasualtyStatusResult:
    """Derive overall and type-specific statuses from final counts and wording.

    ``remaining_total`` maps ``deaths`` and/or ``injuries`` to counts that a
    bulletin total does not account for after summing known location counts.
    If no location breakdown exists, it contains the full unallocated total.
    """
    cleaned = strip_page_header(message_text)
    if is_obituary(cleaned):
        return CasualtyStatusResult(
            status="none_mentioned",
            deaths_status="none_mentioned",
            injuries_status="none_mentioned",
            is_preliminary=False,
            evidence=None,
            remaining_total={},
        )

    deaths_status, deaths_remaining, deaths_evidence = _status_for_kind(
        cleaned, DEATHS, casualties, village_roles, sub_events, target_location_count
    )
    injuries_status, injuries_remaining, injuries_evidence = _status_for_kind(
        cleaned, INJURIES, casualties, village_roles, sub_events, target_location_count
    )
    status = max(
        (deaths_status, injuries_status),
        key=lambda item: _STATUS_PRIORITY[item],
    )
    remaining = {}
    if deaths_status == "aggregate_only" and deaths_remaining is not None:
        remaining[DEATHS] = deaths_remaining
    if injuries_status == "aggregate_only" and injuries_remaining is not None:
        remaining[INJURIES] = injuries_remaining
    evidence = next(
        (
            item
            for item in (deaths_evidence, injuries_evidence)
            if item is not None
        ),
        None,
    )
    return CasualtyStatusResult(
        status=status,
        deaths_status=deaths_status,
        injuries_status=injuries_status,
        is_preliminary=_is_preliminary(cleaned),
        evidence=evidence,
        remaining_total=remaining,
    )


def target_location_count_from_extraction(
    villages: Any,
    village_roles: Any,
    sub_events: Any,
) -> int:
    """Count distinct extracted target locations, including sub-event targets."""
    names: set[str] = set()
    for role in village_roles or ():
        value = _get(role, "role", "target")
        if value not in ("target", getattr(value, "value", None)):
            continue
        name = str(_get(role, "village", "")).strip()
        if name:
            names.add(normalize_casualty_text(name))
    for event in sub_events or ():
        for location in _get(event, "locations", ()) or ():
            value = _get(location, "role", "target")
            if value not in ("target", getattr(value, "value", None)):
                continue
            name = str(_get(location, "village", "")).strip()
            if name:
                names.add(normalize_casualty_text(name))
    if names:
        return len(names)
    return len(
        {
            normalize_casualty_text(str(name).strip())
            for name in villages or ()
            if str(name).strip()
        }
    )


def status_fields(result: CasualtyStatusResult) -> dict[str, Any]:
    """Fields stored on ExtractionResult for backward-compatible JSON persistence."""
    return {
        "casualty_status": result.status,
        "casualty_deaths_status": result.deaths_status,
        "casualty_injuries_status": result.injuries_status,
        "casualty_status_remaining_total": dict(result.remaining_total),
        "casualty_is_preliminary": result.is_preliminary,
        "casualty_status_evidence": result.evidence,
    }


def status_for_incident_row(
    message_text: str,
    extraction: Any,
    row_casualties: Any,
    *,
    target_location_count: int,
) -> CasualtyStatusResult:
    """Use row counts when present; otherwise retain the message-level status."""
    row_has_counts = any(
        _get(row_casualties, field) is not None
        for field in (
            "deaths",
            "injuries",
            "total_deaths",
            "total_injuries",
            "male_deaths",
            "male_injuries",
            "female_deaths",
            "female_injuries",
            "children_deaths",
            "children_injuries",
        )
    )
    if row_has_counts:
        return derive_casualty_status(
            message_text,
            row_casualties,
            target_location_count=1,
        )
    return derive_casualty_status(
        message_text,
        _get(extraction, "casualties"),
        village_roles=_get(extraction, "village_roles", ()),
        sub_events=_get(extraction, "sub_events", ()),
        target_location_count=target_location_count,
    )


_MERGE_PRIORITY = {
    "none_mentioned": 0,
    "explicit_none": 1,
    "count_missing": 2,
    "aggregate_only": 2,
    "exact": 3,
}


def merge_casualty_status(
    current_status: str | None,
    current_is_preliminary: bool,
    current_evidence: str | None,
    incoming_status: str | None,
    incoming_is_preliminary: bool,
    incoming_evidence: str | None,
    *,
    incoming_is_newest: bool,
) -> dict[str, Any]:
    """Merge status while preventing downgrades and clearing stale prelim flags."""
    current = current_status if current_status in _MERGE_PRIORITY else "none_mentioned"
    incoming = incoming_status if incoming_status in _MERGE_PRIORITY else "none_mentioned"
    if _MERGE_PRIORITY[incoming] > _MERGE_PRIORITY[current]:
        status, evidence = incoming, incoming_evidence
    elif _MERGE_PRIORITY[incoming] < _MERGE_PRIORITY[current]:
        status, evidence = current, current_evidence
    elif incoming_is_newest:
        status, evidence = incoming, incoming_evidence or current_evidence
    else:
        status, evidence = current, current_evidence
    preliminary = (
        bool(incoming_is_preliminary)
        if incoming_is_newest
        else bool(current_is_preliminary)
    )
    return {
        "casualty_status": status,
        "casualty_is_preliminary": preliminary,
        "casualty_status_evidence": evidence,
    }
