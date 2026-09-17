from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.text_normalization import normalize_arabic_text
from app.news.services.air_violations.caza_alias_resolver import resolve_caza_alias


@dataclass(frozen=True)
class AirViolationExclusion:
    reason: str
    evidence_span: str


_UNIFIL_RE = re.compile(r"(يونيفيل|اليونيفيل|unifil)", re.IGNORECASE)
_AIRCRAFT_RE = re.compile(
    r"(طائرة|طيران|مروحية|مسيرة|مسيّرة|درون|helicopter|aircraft|drone|plane)",
    re.IGNORECASE,
)
_PALESTINE_ROUTE_RE = re.compile(
    r"(?:من|انطلاقا من)\s+فلسطين\s+(?:باتجاه|نحو|الى|إلى)|from\s+palestine\s+(?:toward|towards|to)",
    re.IGNORECASE,
)
_LEBANESE_AIRSPACE_RE = re.compile(
    r"(?:فوق|في اجواء|في أجواء|داخل الاجواء|داخل الأجواء|يحلق فوق|تحليق فوق)",
    re.IGNORECASE,
)


def _span(text: str, match: re.Match[str] | None) -> str:
    if match is None:
        return text[:80].strip()
    start = max(0, match.start() - 20)
    end = min(len(text), match.end() + 40)
    return text[start:end].strip()


def _has_concrete_lebanese_violation(text: str) -> bool:
    if not _LEBANESE_AIRSPACE_RE.search(text):
        return False
    if resolve_caza_alias(text):
        return True
    normalized = normalize_arabic_text(text)
    return any(marker in normalized for marker in ("قضاء", "بلدة", "مدينة", "الجنوب", "لبنان"))


def air_violation_exclusion(text: str | None) -> AirViolationExclusion | None:
    value = (text or "").strip()
    if not value:
        return None

    unifil = _UNIFIL_RE.search(value)
    if unifil and _AIRCRAFT_RE.search(value):
        return AirViolationExclusion(
            reason="excluded_unifil_aircraft",
            evidence_span=_span(value, unifil),
        )

    route = _PALESTINE_ROUTE_RE.search(value)
    if route and _AIRCRAFT_RE.search(value) and not _has_concrete_lebanese_violation(value):
        return AirViolationExclusion(
            reason="excluded_origin_route_palestine",
            evidence_span=_span(value, route),
        )

    return None
