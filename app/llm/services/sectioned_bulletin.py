"""Deterministic recovery for heading-and-location incident bulletins.

Some feeds publish a compact table as plain text: an action heading on one
line followed by one or more location lines.  A whole-message LLM can mistake
the later locations for alternatives to the first one.  This module only
handles the conservative shape where at least two known action headings are
present; ordinary prose remains entirely model-driven.
"""

from __future__ import annotations

import re

from app.core.text_normalization import normalize_arabic_text
from app.llm.dtos import ExtractionCasualties, ExtractionSubEvent, VillageRoleEntry


_BULLET_PREFIX_RE = re.compile(r"^[\s•●◦▪▫\-*–—]+")
_BETWEEN_RE = re.compile(
    r"^بين(?:\s+بلدتي)?\s+(?P<left>.+?)\s+و(?P<right>.+?)$"
)
_URL_OR_FOOTER_RE = re.compile(r"(?:https?://|www\.|#\S+|المصدر\s*:)", re.IGNORECASE)


def _heading_action(line: str) -> str | None:
    normalized = normalize_arabic_text(line.strip(" :ـ-–—"))
    if not normalized:
        return None
    patterns = (
        r"(?:الغارات?|غارات?)\s+(?:الحربيه\s+)?(?:المعاديه|الاسرائيليه)?",
        r"(?:القصف\s+)?المدفعي(?:\s+(?:المعادي|الاسرائيلي))?",
        r"التفجيرات?",
        r"قنابل\s+(?:مضيئه|اناره|ضوئيه)",
        r"(?:عمليات\s+)?التمشيط(?:\s+بالاسلحه\s+الرشاشه)?",
    )
    if any(re.fullmatch(pattern, normalized) for pattern in patterns):
        return line.strip(" :ـ-–—")
    return None


def _location_entries(line: str) -> list[VillageRoleEntry]:
    cleaned = _BULLET_PREFIX_RE.sub("", line).strip(" ،,;؛:ـ-–—")
    if not cleaned or _URL_OR_FOOTER_RE.search(cleaned):
        return []
    between = _BETWEEN_RE.fullmatch(normalize_arabic_text(cleaned))
    if between is not None:
        evidence = cleaned
        return [
            VillageRoleEntry(
                village=between.group("left").strip(),
                evidence_span=evidence,
            ),
            VillageRoleEntry(
                village=between.group("right").strip(),
                evidence_span=evidence,
            ),
        ]
    parts = [part.strip() for part in re.split(r"[،,]", cleaned) if part.strip()]
    return [VillageRoleEntry(village=part, evidence_span=cleaned) for part in parts]


def recover_sectioned_sub_events(post_text: str) -> list[ExtractionSubEvent]:
    """Return action-scoped events for a conservative sectioned-list shape."""
    lines = [line.strip() for line in (post_text or "").splitlines() if line.strip()]
    headings = [index for index, line in enumerate(lines) if _heading_action(line)]
    if len(headings) < 2:
        return []

    events: list[ExtractionSubEvent] = []
    for position, heading_index in enumerate(headings):
        end = headings[position + 1] if position + 1 < len(headings) else len(lines)
        action = _heading_action(lines[heading_index])
        if action is None:
            continue
        locations: list[VillageRoleEntry] = []
        section_lines: list[str] = [lines[heading_index]]
        for line in lines[heading_index + 1 : end]:
            section_lines.append(line)
            locations.extend(_location_entries(line))
        if not locations:
            continue
        events.append(
            ExtractionSubEvent(
                locations=locations,
                action_text=action,
                casualties=ExtractionCasualties(),
                evidence_span="\n".join(section_lines),
            )
        )

    return events if len(events) >= 2 else []


def target_pair_count(events: list[ExtractionSubEvent]) -> int:
    return sum(len(event.locations) for event in events)
