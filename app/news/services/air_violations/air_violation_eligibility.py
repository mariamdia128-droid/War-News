from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.text_normalization import normalize_arabic_text
from app.news.services.air_violations.caza_alias_resolver import resolve_caza_alias


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reason: str
    matched_terms: list[str]


_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_HASHTAG_RE = re.compile(r"#[^\s#]+")
_HANDLE_RE = re.compile(r"(?<!\w)@[\w.]+")
_LEADING_SOURCE_RE = re.compile(
    r"^\s*(?:(?:عاجل|حصري)\s*[|:\-–—]*\s*)?"
    r"(?:(?:صفحه|صفحة)\s+)?(?:الاعلامي|الإعلامي|مراسل(?:نا|\s+[^:|]+)?)"
    r"\s+(?:الشهيد\s+)?[^:\n|]{2,80}\s*[:|\-–—]\s*",
    re.IGNORECASE,
)
_TITLE_LINE_RE = re.compile(
    r"^\s*(?:(?:صفحه|صفحة)\s+)?(?:الاعلامي|الإعلامي)\s+الشهيد\s+[^:\n]{2,80}\s*$",
    re.IGNORECASE,
)
_HONORIFIC_PREFIX_RE = re.compile(
    r"^\s*(?:الشهيد\s+(?:القائد|الاعلامي|الإعلامي)|الشهيد)\s+[^:\n]{2,80}\s*[:\-–—]\s*",
    re.IGNORECASE,
)

_UNIFIL_TERMS = ("يونيفيل", "اليونيفيل", "unifil")
_AIRCRAFT_TERMS = (
    "طائره", "طيران", "مروحيه", "مسيره", "درون", "helicopter", "aircraft", "drone", "plane",
)
_STATUS_UPDATE_TERMS = (
    "اخر تحديث للمناطق المتاثره",
    "عدد الدوائر الحمراء يدل علي عدد المناطق المتاثره",
)

_STRIKE_TERMS = (
    "غاره", "غارات", "غارت", "اغار", "استهدف", "استهداف", "استهدفت", "قصف", "قصفت",
    "اغتيال", "اطلاق صاروخ", "صاروخ", "قنبله", "قنابل", "انفجار",
    "تفجير", "قذيفه", "قذائف", "مدفعيه", "airstrike", "air strike", "attacked", "strike",
)
_CASUALTY_TERMS = (
    "شهيد", "شهداء", "استشهاد", "استشهد", "جريح", "جرحي", "اصابه",
    "اصابات", "قتل", "قتيل", "قتلي", "نجاه", "ناج", "ضحايا",
)
_DAMAGE_TERMS = ("تدمير", "دمار", "اضرار", "تضرر", "احتراق")
_FIRE_TERMS = ("حريق",)
_APACHE_TERMS = ("اباتشي", "apache", "ah-64")


def _unwrap_hashtags(value: str) -> str:
    return _HASHTAG_RE.sub(lambda match: " " + match.group(0)[1:].replace("_", " "), value)


def _strip_source_noise(value: str, *, keep_hashtags: bool = False) -> str:
    value = _URL_RE.sub(" ", value)
    value = _unwrap_hashtags(value) if keep_hashtags else _HASHTAG_RE.sub(" ", value)
    value = _HANDLE_RE.sub(" ", value)
    kept: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line or _TITLE_LINE_RE.match(line):
            continue
        line = _LEADING_SOURCE_RE.sub("", line)
        line = _HONORIFIC_PREFIX_RE.sub("", line)
        if line.strip():
            kept.append(line.strip())
    return "\n".join(kept)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", normalize_arabic_text(value).casefold()).strip()


def cleaned_air_violation_text(text: str | None) -> str:
    """Strip source noise, then normalize Arabic for term matching.

    Hashtags are dropped because trailing tag lists ("#شهيد") describe a feed,
    not the event. Red Alert posts are hashtags only, though, so when dropping
    them would leave nothing the tags are unwrapped and kept as the content.
    """
    raw = text or ""
    cleaned = _normalize(_strip_source_noise(raw))
    if cleaned:
        return cleaned
    return _normalize(_strip_source_noise(raw, keep_hashtags=True))


def _matched_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    return list(dict.fromkeys(term for term in terms if term.casefold() in text))


def _has_concrete_lebanese_violation(text: str) -> bool:
    if not any(term in text for term in ("فوق", "في اجواء", "داخل الاجواء", "يحلق فوق", "تحليق فوق")):
        return False
    if resolve_caza_alias(text):
        return True
    return any(marker in text for marker in ("قضاء", "بلده", "مدينه", "الجنوب", "لبنان"))


def evaluate_air_violation_text(text: str | None) -> EligibilityResult:
    """Decide whether text describes presence-only air activity."""
    cleaned = cleaned_air_violation_text(text)
    if not cleaned:
        return EligibilityResult(False, "empty_text", [])

    status_terms = _matched_terms(cleaned, _STATUS_UPDATE_TERMS)
    if status_terms:
        return EligibilityResult(False, "excluded_red_alert_status_update", status_terms)

    unifil_terms = _matched_terms(cleaned, _UNIFIL_TERMS)
    if unifil_terms and _matched_terms(cleaned, _AIRCRAFT_TERMS):
        return EligibilityResult(False, "excluded_unifil_aircraft", unifil_terms)

    route_terms = _matched_terms(cleaned, ("من فلسطين باتجاه", "من فلسطين نحو", "from palestine toward", "from palestine to"))
    if route_terms and _matched_terms(cleaned, _AIRCRAFT_TERMS) and not _has_concrete_lebanese_violation(cleaned):
        return EligibilityResult(False, "excluded_origin_route_palestine", route_terms)

    strike_terms = _matched_terms(cleaned, _STRIKE_TERMS)
    casualty_terms = _matched_terms(cleaned, _CASUALTY_TERMS)
    damage_terms = _matched_terms(cleaned, _DAMAGE_TERMS)
    fire_terms = _matched_terms(cleaned, _FIRE_TERMS) if strike_terms else []
    apache_terms = _matched_terms(cleaned, _APACHE_TERMS) if strike_terms else []
    rejected_terms = list(dict.fromkeys([
        *strike_terms,
        *casualty_terms,
        *damage_terms,
        *fire_terms,
        *apache_terms,
    ]))
    if rejected_terms:
        return EligibilityResult(False, "excluded_kinetic_casualty_or_damage", rejected_terms)

    return EligibilityResult(True, "presence_only", [])
