"""Split one raw message into news items ("segments") for split-phase Tier 1.

Pure functions, no LLM. Segments are contiguous character spans of the input:
concatenating ``post_text[s.start:s.end]`` over all segments gives back the
whole input, so any evidence span returned for a segment can be checked
against both the segment and the original message.

Split points, strongest first:

1. Item markers inside a block: numbered lines («1-», «٢.», «(3)»), bullets
   («•», «-», «▪»), or a leading symbol/word repeated on two or more lines
   («🔴», «عاجل:»). Needs at least two marker lines in the block.
2. Blank-line blocks.
3. Secondary-event connectors at a sentence boundary («. كما غارة أخرى في
   بلدة X»), only when the new sentence opens a new event: it names a village
   not seen earlier in the segment, or it says «غارة أخرى / استهداف آخر».
   A connector that continues the same item («كما أصيب 3 آخرون») never splits.

Pieces without any event cue (source footers, hashtags, a lone headline) are
merged into a neighbour. When nothing splits, the whole text is one segment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.llm_knowledge.loader import terms_by_category

# Mirrors the connector alternation of ``_SECONDARY_EVENT_CONNECTOR_RE`` in
# ollama_extraction_service.py, plus «فيما» used by accuracy-study bulletins.
SECONDARY_EVENT_CONNECTORS: tuple[str, ...] = (
    "كما",
    "فيما",
    "أيضا",
    "أيضاً",
    "بالإضافة إلى",
    "بالإضافة",
    "من جهة أخرى",
    "وفي سياق متصل",
)

_ARABIC_DIACRITICS = frozenset(chr(code) for code in range(0x064B, 0x0653)) | {"ـ"}
_FOLD_TABLE = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي"})


def _fold(text: str) -> str:
    """Normalize spelling without changing length (diacritics become spaces)."""
    folded = "".join(" " if ch in _ARABIC_DIACRITICS else ch for ch in text)
    return folded.translate(_FOLD_TABLE)


def _folded_terms(*sources: tuple[str, str]) -> tuple[str, ...]:
    collected: list[str] = []
    for relative_path, category in sources:
        for term in terms_by_category(relative_path, category):
            folded = " ".join(_fold(term).split())
            if folded:
                collected.append(folded)
    return tuple(dict.fromkeys(collected))


_EVENT_CUE_TERMS = _folded_terms(
    ("terminology/role_terms.yaml", "targeting_verb"),
    ("terminology/role_terms.yaml", "direct_impact_term"),
    ("terminology/role_terms.yaml", "air_platform"),
    ("terminology/casualty_wording.yaml", "death_term"),
    ("terminology/casualty_wording.yaml", "injury_term"),
    ("terminology/casualty_wording.yaml", "strike_heading"),
)
_VILLAGE_MARKERS = _folded_terms(
    ("terminology/role_terms.yaml", "village_location_marker"),
) or ("بلده", "مدينه", "قريه")

_NUMBERED_RE = re.compile(
    r"^[ \t]*(?:\(?[0-9٠-٩]{1,2}\s*[-.)\]:–—]|\([0-9٠-٩]{1,2}\))[ \t]*"
)
_BULLET_RE = re.compile(r"^[ \t]*[•●○◦▪▫■□◾◽▸►\-*–—·][️]?[ \t]+")
# A run of symbols/emoji (no letters or digits) at line start, e.g. «🔴», «📍».
_SYMBOL_LEAD_RE = re.compile(
    r"^[ \t]*([^\w\s؀-ۿ()\[\]«»\"'.,:;،؛؟!]{1,4})[ \t]*"
)
_WORD_LEAD_RE = re.compile(r"^[ \t]*(عاجل|خاص|متابعة)[ \t]*[:：|\-–—]")
_BLANK_LINE_RE = re.compile(r"\n[ \t]*\n\s*")
_SENTENCE_END_RE = re.compile(r"[.؛;!؟\n]\s*")
_ANOTHER_EVENT_RE = re.compile(
    r"(?:غاره|غارات|قصف|استهداف|ضربه|هجوم)\s+(?:\S+\s+){0,2}?(?:اخري|اخر|ثانيه|ثان)(?![؀-ۿ])"
)


@dataclass(frozen=True)
class TextSegment:
    """One news item: ``post_text[start:end]`` of the original message."""

    index: int
    start: int
    end: int
    raw: str
    # Lines before the first item marker of a list block («الغارات اليوم:»).
    # Context for the LLM only; evidence must come from ``text``.
    header: str | None = None

    @property
    def text(self) -> str:
        return self.raw.strip()


def split_segments(post_text: str) -> list[TextSegment]:
    """Split *post_text* into contiguous item segments (at least one)."""
    text = post_text or ""
    if not text.strip():
        return [TextSegment(index=0, start=0, end=len(text), raw=text)]

    pieces: list[tuple[int, int, str | None]] = []
    for block_start, block_end in _blank_line_blocks(text):
        items, header = _item_marker_spans(text, block_start, block_end)
        if items:
            for item_start, item_end in items:
                pieces.append((item_start, item_end, header))
            continue
        for sent_start, sent_end in _connector_spans(text, block_start, block_end):
            pieces.append((sent_start, sent_end, None))

    pieces = _merge_cueless(text, pieces)
    # Make the spans contiguous so the segments cover the whole input.
    segments: list[TextSegment] = []
    for index, (start, _end, header) in enumerate(pieces):
        start = 0 if index == 0 else start
        end = pieces[index + 1][0] if index + 1 < len(pieces) else len(text)
        segments.append(
            TextSegment(
                index=index,
                start=start,
                end=end,
                raw=text[start:end],
                header=header,
            )
        )
    return segments


def has_event_cue(text: str) -> bool:
    folded = " ".join(_fold(text).split())
    return any(term in folded for term in _EVENT_CUE_TERMS)


def _blank_line_blocks(text: str) -> list[tuple[int, int]]:
    blocks: list[tuple[int, int]] = []
    cursor = 0
    for match in _BLANK_LINE_RE.finditer(text):
        if text[cursor : match.start()].strip():
            blocks.append((cursor, match.start()))
        cursor = match.end()
    if text[cursor:].strip():
        blocks.append((cursor, len(text)))
    return blocks or [(0, len(text))]


def _line_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = start
    while cursor < end:
        newline = text.find("\n", cursor, end)
        line_end = end if newline < 0 else newline
        if text[cursor:line_end].strip():
            spans.append((cursor, line_end))
        cursor = line_end + 1
    return spans


def _marker_kind(line: str) -> str | None:
    if _NUMBERED_RE.match(line):
        return "numbered"
    if _BULLET_RE.match(line):
        return "bullet"
    match = _WORD_LEAD_RE.match(line)
    if match:
        return f"word:{match.group(1)}"
    match = _SYMBOL_LEAD_RE.match(line)
    if match:
        return f"symbol:{match.group(1)}"
    return None


def _item_marker_spans(
    text: str,
    start: int,
    end: int,
) -> tuple[list[tuple[int, int]], str | None]:
    """Item spans for a block whose lines carry repeated item markers."""
    lines = _line_spans(text, start, end)
    kinds = [_marker_kind(text[line_start:line_end]) for line_start, line_end in lines]
    counts: dict[str, int] = {}
    for kind in kinds:
        if kind is not None:
            counts[kind] = counts.get(kind, 0) + 1
    # Numbered and bullet markers count together: «1-» lists often mix «-».
    list_kinds = {kind for kind in counts if kind in {"numbered", "bullet"}}
    list_total = sum(counts[kind] for kind in list_kinds)
    marker_kinds: set[str]
    if list_total >= 2:
        marker_kinds = list_kinds
    else:
        repeated = [kind for kind, count in counts.items() if count >= 2]
        if not repeated:
            return [], None
        marker_kinds = set(repeated)

    item_starts = [
        line_start
        for (line_start, _line_end), kind in zip(lines, kinds, strict=True)
        if kind in marker_kinds
    ]
    first = item_starts[0]
    header_text = text[start:first].strip() or None
    spans = [
        (item_start, item_starts[position + 1] if position + 1 < len(item_starts) else end)
        for position, item_start in enumerate(item_starts)
    ]
    # The header stays inside the first item span so the spans still cover
    # the block; it is also passed on as context for every item.
    spans[0] = (start, spans[0][1])
    return spans, header_text


def _connector_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Split one block at connector-led sentences that open a new event."""
    folded = _fold(text)
    connectors = tuple(
        " ".join(_fold(connector).split()) for connector in SECONDARY_EVENT_CONNECTORS
    )
    cut_points: list[int] = []
    segment_start = start
    for boundary in _SENTENCE_END_RE.finditer(text, start, end):
        sentence_start = boundary.end()
        if sentence_start >= end:
            continue
        sentence_folded = folded[sentence_start:end]
        # «وكما» / «وفيما» are the same connectors with a leading conjunction.
        probes = [sentence_folded]
        if sentence_folded.startswith("و"):
            probes.append(sentence_folded[1:])
        if not any(
            probe.startswith(connector)
            and (len(probe) == len(connector) or not _is_arabic_letter(probe[len(connector)]))
            for probe in probes
            for connector in connectors
        ):
            continue
        sentence_end = _sentence_end(text, sentence_start, end)
        sentence = folded[sentence_start:sentence_end]
        previous = folded[segment_start:sentence_start]
        if _ANOTHER_EVENT_RE.search(sentence) or _names_new_village(sentence, previous):
            cut_points.append(sentence_start)
            segment_start = sentence_start
    bounds = [start, *cut_points, end]
    return [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]


def _sentence_end(text: str, start: int, end: int) -> int:
    match = _SENTENCE_END_RE.search(text, start, end)
    return end if match is None else match.start()


def _is_arabic_letter(ch: str) -> bool:
    return "ء" <= ch <= "ي"


def _names_new_village(sentence: str, previous: str) -> bool:
    """True when *sentence* has «بلدة X» and X does not appear in *previous*."""
    previous_compact = " ".join(previous.split())
    for marker in _VILLAGE_MARKERS:
        for match in re.finditer(
            rf"(?<![؀-ۿ]){re.escape(marker)}\s+([؀-ۿ]{{2,}})",
            sentence,
        ):
            name = match.group(1)
            if re.search(rf"(?<![؀-ۿ]){re.escape(name)}(?![؀-ۿ])", previous_compact):
                continue
            return True
    return False


def _merge_cueless(
    text: str,
    pieces: list[tuple[int, int, str | None]],
) -> list[tuple[int, int, str | None]]:
    """Fold pieces with no event cue into the previous (or next) piece."""
    if len(pieces) <= 1:
        return pieces or [(0, len(text), None)]
    merged: list[tuple[int, int, str | None]] = []
    pending_start: int | None = None
    for start, end, header in pieces:
        piece_has_cue = has_event_cue(text[start:end])
        # List items stay separate even without a cue: «• حولا (٢)» is an item.
        is_list_item = header is not None or _marker_kind(text[start:end].lstrip("\n")) in {
            "numbered",
            "bullet",
        }
        if piece_has_cue or is_list_item:
            if pending_start is not None:
                start = pending_start
                pending_start = None
            merged.append((start, end, header))
        elif merged:
            prev_start, _prev_end, prev_header = merged[-1]
            merged[-1] = (prev_start, end, prev_header)
        elif pending_start is None:
            pending_start = start
    if pending_start is not None:
        # Only reachable when no piece had a cue: keep the text as one item.
        merged.append((pending_start, pieces[-1][1], None))
    return merged
