"""Evidence-backed Arabic condition aliases for similarity matching.

Alias *phrases* live in ``llm_knowledge/terminology/condition_labels.yaml``.
This module rebuilds the runtime ``CONDITION_ALIASES`` map for
``ConditionRepository.find_similar``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.llm_knowledge.loader import load_terminology


@dataclass(frozen=True)
class ConditionAlias:
    text: str
    raw_message_ids: tuple[int, ...]


def _parse_raw_message_ids(notes: str | None) -> tuple[int, ...]:
    if not notes or "raw_message_ids=" not in notes:
        return ()
    payload = notes.split("raw_message_ids=", 1)[1].split(";", 1)[0].strip()
    if not payload:
        return ()
    return tuple(int(part.strip()) for part in payload.split(",") if part.strip())


def _load_condition_aliases() -> dict[str, tuple[ConditionAlias, ...]]:
    grouped: dict[str, list[ConditionAlias]] = {}
    for entry in load_terminology("terminology/condition_labels.yaml"):
        if entry.category != "condition_alias":
            continue
        grouped.setdefault(entry.meaning, []).append(
            ConditionAlias(
                text=entry.term,
                raw_message_ids=_parse_raw_message_ids(entry.notes),
            )
        )
    return {key: tuple(values) for key, values in grouped.items()}


CONDITION_ALIASES: dict[str, tuple[ConditionAlias, ...]] = _load_condition_aliases()
