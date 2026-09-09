from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.text_normalization import normalize_arabic_text


@dataclass(frozen=True)
class StoryRevisionBackstopResult:
    plausible: bool
    relationship_hint: str | None
    matched_keywords: tuple[str, ...]
    evidence: str | None


_REVISION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("حصيلة أولية", re.compile(r"حصيله اوليه")),
    ("حصيلة مؤقتة", re.compile(r"حصيله مؤقته")),
    ("تحديث الحصيلة", re.compile(r"تحديث الحصيله")),
    ("ارتفاع عدد الشهداء/الجرحى", re.compile(r"ارتفاع عدد.{0,20}(?:الشهداء|الجرحى|الشهيد|الجريح)")),
    ("ارتفع عدد", re.compile(r"ارتفع عدد.{0,20}(?:الشهداء|الجرحى|الشهيد|الجريح)")),
    ("المعلومات الأولية", re.compile(r"المعلومات الاوليه")),
    ("معلومات أولية", re.compile(r"معلومات اوليه")),
)

_NAMED_VICTIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("تنعى", re.compile(r"تنعي")),
    ("الموظفة/الموظف named martyr", re.compile(r"الموظف(?:ه)?.{0,40}(?:ارتقت|ارتقى|استشهد|شهيد)")),
    ("الشهيدة + given name", re.compile(r"الشهيده\s+\S{2,}\s+\S{2,}")),
    ("زهراء-style full name + martyrdom", re.compile(r"[\u0600-\u06ff]{3,}\s+[\u0600-\u06ff]{3,}.{0,40}(?:ارتقت|استشهدت|شهيده)")),
)

_NUMERIC_TOLL = re.compile(r"[0-9٠-٩]+")
_NAMED_IN_CANDIDATE = re.compile(r"تنعي|الشهيده\s+\S{2,}\s+\S{2,}")


def story_revision_keyword_labels() -> tuple[str, ...]:
    return tuple(label for label, _ in _REVISION_PATTERNS) + tuple(
        label for label, _ in _NAMED_VICTIM_PATTERNS
    )


def detect_story_revision_backstop(
    text: str | None,
    *,
    candidate_text: str | None = None,
    candidate_deaths: int | None = None,
    candidate_injuries: int | None = None,
) -> StoryRevisionBackstopResult:
    """Keyword/regex backstop for revision and named-victim follow-ups."""
    normalized = normalize_arabic_text(text or "")
    if not normalized:
        return StoryRevisionBackstopResult(
            plausible=False,
            relationship_hint=None,
            matched_keywords=(),
            evidence=None,
        )

    revision_hits = tuple(
        label for label, pattern in _REVISION_PATTERNS if pattern.search(normalized)
    )
    named_hits = tuple(
        label for label, pattern in _NAMED_VICTIM_PATTERNS if pattern.search(normalized)
    )

    if revision_hits:
        return StoryRevisionBackstopResult(
            plausible=True,
            relationship_hint="revision",
            matched_keywords=revision_hits,
            evidence=revision_hits[0],
        )

    if named_hits and _candidate_has_numeric_toll_without_names(
        candidate_text,
        candidate_deaths=candidate_deaths,
        candidate_injuries=candidate_injuries,
    ):
        return StoryRevisionBackstopResult(
            plausible=True,
            relationship_hint="revision",
            matched_keywords=named_hits,
            evidence=named_hits[0],
        )

    return StoryRevisionBackstopResult(
        plausible=False,
        relationship_hint=None,
        matched_keywords=(),
        evidence=None,
    )


def _candidate_has_numeric_toll_without_names(
    candidate_text: str | None,
    *,
    candidate_deaths: int | None,
    candidate_injuries: int | None,
) -> bool:
    has_counts = any(
        isinstance(value, int) and not isinstance(value, bool) and value > 0
        for value in (candidate_deaths, candidate_injuries)
    )
    normalized = normalize_arabic_text(candidate_text or "")
    if not has_counts:
        has_counts = bool(_NUMERIC_TOLL.search(normalized))
    if not has_counts:
        return False
    return _NAMED_IN_CANDIDATE.search(normalized) is None
