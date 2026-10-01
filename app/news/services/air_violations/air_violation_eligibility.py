from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.text_normalization import normalize_arabic_text
from app.news.services.air_violations.caza_alias_resolver import resolve_caza_alias


#: The one exclusion that means "a real event happened, it just is not an air
#: violation". Only these rows belong in the incident pipeline; every other
#: exclusion is a notice, a tag or an unreadable row, and goes to a human.
KINETIC_EXCLUSION_REASON = "excluded_kinetic_casualty_or_damage"


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reason: str
    matched_terms: list[str]

    @property
    def belongs_in_incidents(self) -> bool:
        """True when rejecting this text means it is an incident report."""
        return not self.eligible and self.reason == KINETIC_EXCLUSION_REASON


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
# End-of-day digests and channel housekeeping posts list kinetic words without
# reporting an event ("...a drone, or a warplane, or an airstrike..."), so they
# must be recognised before the kinetic terms are matched. Mirrors the
# collector's NON_EVENT_NOTICE_PARTS / NON_AIR_DRONE_WORD_PATTERNS.
_NON_EVENT_NOTICE_TERMS = (
    "احصاءات نهايه اليوم",
    "احصاء التنبيهات",
    "اجمالي التنبيهات",
    "اكثر القري رصدا",
    "اكثر الاقضيه نشاطا",
    "جزء من هذه المسيره",
    "بدانا بمجموعه",
    "نرجو منكم ابلاغنا فورا",
    "عبر البوت الجديد",
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
# Terms are matched as substrings so Arabic inflections (غارة/غارات/غارتان)
# all count, which also makes place names that merely contain one of them look
# kinetic. "نهر المغارة" is a river, not a غارة.
_KINETIC_LOOKALIKE_RE = re.compile(r"(?<![^\W\d_])(?:ال)?مغار(?:ه|ات)(?![^\W\d_])")


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


def _clean_with_provenance(text: str | None) -> tuple[str, bool]:
    """Return the matchable text and whether it came only from hashtags.

    Hashtags are dropped because trailing tag lists ("#شهيد") label a feed
    rather than reporting an event. Red Alert posts are hashtags only, though,
    so when dropping them would leave nothing the tags are unwrapped and kept
    as the content -- and the caller is told, because a bare "#الشهيد" is a
    label, not a casualty report.
    """
    raw = text or ""
    cleaned = _normalize(_strip_source_noise(raw))
    if cleaned:
        return cleaned, False
    return _normalize(_strip_source_noise(raw, keep_hashtags=True)), True


def cleaned_air_violation_text(text: str | None) -> str:
    return _clean_with_provenance(text)[0]


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
    cleaned, hashtags_only = _clean_with_provenance(text)
    if not cleaned:
        return EligibilityResult(False, "empty_text", [])

    status_terms = _matched_terms(cleaned, _STATUS_UPDATE_TERMS)
    if status_terms:
        return EligibilityResult(False, "excluded_red_alert_status_update", status_terms)

    notice_terms = _matched_terms(cleaned, _NON_EVENT_NOTICE_TERMS)
    if notice_terms:
        return EligibilityResult(False, "excluded_non_event_notice", notice_terms)

    unifil_terms = _matched_terms(cleaned, _UNIFIL_TERMS)
    if unifil_terms and _matched_terms(cleaned, _AIRCRAFT_TERMS):
        return EligibilityResult(False, "excluded_unifil_aircraft", unifil_terms)

    route_terms = _matched_terms(cleaned, ("من فلسطين باتجاه", "من فلسطين نحو", "from palestine toward", "from palestine to"))
    if route_terms and _matched_terms(cleaned, _AIRCRAFT_TERMS) and not _has_concrete_lebanese_violation(cleaned):
        return EligibilityResult(False, "excluded_origin_route_palestine", route_terms)

    matchable = _KINETIC_LOOKALIKE_RE.sub(" ", cleaned)
    strike_terms = _matched_terms(matchable, _STRIKE_TERMS)
    casualty_terms = _matched_terms(matchable, _CASUALTY_TERMS)
    damage_terms = _matched_terms(matchable, _DAMAGE_TERMS)
    fire_terms = _matched_terms(matchable, _FIRE_TERMS) if strike_terms else []
    apache_terms = _matched_terms(matchable, _APACHE_TERMS) if strike_terms else []
    rejected_terms = list(dict.fromkeys([
        *strike_terms,
        *casualty_terms,
        *damage_terms,
        *fire_terms,
        *apache_terms,
    ]))
    if rejected_terms:
        if hashtags_only:
            # The only evidence is a bare tag ("#الشهيد"), which labels a feed
            # and reports nothing. Too thin to call an incident, so it goes to
            # a human rather than into the incident pipeline.
            return EligibilityResult(False, "excluded_hashtag_only_ambiguous", rejected_terms)
        return EligibilityResult(False, KINETIC_EXCLUSION_REASON, rejected_terms)

    return EligibilityResult(True, "presence_only", [])
