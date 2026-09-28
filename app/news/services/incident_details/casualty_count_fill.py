"""Deterministic count fill for bare singular / dual casualty words.

The LLM often returns null for «شهيدان» (2), «جريحان» (2), «شهيد» (1) or
«ثلاثة شهداء» (3). When the message names exactly one target location, the
word sits in the same sentence as that location, and nothing makes the count
ambiguous, the count is filled here with a verbatim evidence span.

Multi-location messages are never filled: the word may belong to any village.
"""

from __future__ import annotations

import logging

from app.core.text_normalization import normalize_arabic_text
from app.llm.dtos import CasualtyCountEvidence, ExtractionCasualties
from app.news.services.incident_details.casualty_text import (
    DEATHS,
    INJURIES,
    CountMention,
    find_count_mentions,
    has_explicit_none,
    is_obituary,
    mentions_named_victim,
    sentences,
    strip_page_header,
)

logger = logging.getLogger(__name__)

_FILL_RULES = frozenset({"singular", "dual", "spelled_number"})


def _village_key(name: str) -> str:
    return normalize_arabic_text(name, compact=True)


def _sentence_mentions(sentence: str, kind: str) -> list[CountMention]:
    return [m for m in find_count_mentions(sentence) if m.kind == kind]


def fill_counts_from_count_words(
    text: str,
    casualties: ExtractionCasualties,
    evidence: list[CasualtyCountEvidence],
    *,
    target_villages: list[str],
    raw_message_id: int | None = None,
) -> tuple[ExtractionCasualties, list[CasualtyCountEvidence]]:
    """Fill null deaths/injuries from explicit count words in a single-target message."""
    targets = {_village_key(name) for name in target_villages if name and name.strip()}
    if len(targets) != 1 or is_obituary(text):
        return casualties, evidence
    (target,) = targets

    # Skip sentences that talk about a named, already-known victim.
    usable = [
        sentence
        for sentence in sentences(strip_page_header(text))
        if not mentions_named_victim(sentence) and not is_obituary(sentence)
    ]
    values = casualties.model_dump(mode="python")
    kept = list(evidence)

    for kind in (DEATHS, INJURIES):
        total_field = f"total_{kind}"
        if values.get(kind) is not None or values.get(total_field) is not None:
            continue
        if has_explicit_none(text, kind):
            continue
        found: list[tuple[CountMention, bool]] = []
        ambiguous = False
        for sentence in usable:
            mentions = _sentence_mentions(sentence, kind)
            if any(m.rule not in _FILL_RULES for m in mentions):
                # A digit count the LLM dropped: leave it for review, don't guess.
                ambiguous = True
                break
            in_target_sentence = target in _village_key(sentence)
            found.extend((m, in_target_sentence) for m in mentions)
        if ambiguous or not found:
            continue
        counts = {mention.value for mention, _ in found}
        if len(counts) != 1 or not any(same_sentence for _, same_sentence in found):
            continue
        mention = next(m for m, same_sentence in found if same_sentence)
        values[kind] = mention.value
        values[total_field] = mention.value
        for field in (kind, total_field):
            kept.append(CasualtyCountEvidence(field=field, evidence_span=mention.text))
        logger.info(
            "casualty_count_fill filled field=%s value=%s rule=%s evidence=%r "
            "raw_message_id=%s",
            kind,
            mention.value,
            mention.rule,
            mention.text,
            raw_message_id,
        )

    return ExtractionCasualties.model_validate(values), kept
