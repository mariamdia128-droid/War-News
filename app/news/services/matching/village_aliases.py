"""Neighborhood / city-mention aliases that resolve to a parent village.

Proposed seed rows are stored in
``llm_knowledge/terminology/village_aliases.yaml`` (and mirrored in
``Data/VillageLocationAliases.json`` for DB seeding). Runtime matching uses
the ``village_location_aliases`` table, not this catalog directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.llm_knowledge.loader import load_terminology


@dataclass(frozen=True)
class VillageLocationAliasProposal:
    """Proposed seed row. ``parent_acs_code`` is the stable key across envs."""

    alias_text: str
    parent_acs_code: int
    note: str
    confidence: str  # "proposed" | "uncertain"
    evidence: str


def _load_proposed_aliases() -> tuple[VillageLocationAliasProposal, ...]:
    proposals: list[VillageLocationAliasProposal] = []
    for entry in load_terminology("terminology/village_aliases.yaml"):
        if entry.category != "village_location_alias":
            continue
        meaning = entry.meaning or ""
        if not meaning.startswith("acs:"):
            continue
        acs_code = int(meaning.removeprefix("acs:"))
        notes = entry.notes or ""
        confidence = "proposed"
        if "confidence=" in notes:
            confidence = notes.split("confidence=", 1)[1].split(";", 1)[0].strip()
        evidence = ""
        if ";" in notes:
            evidence = notes.split(";", 1)[1].strip()
        note = notes.split("confidence=", 1)[0].strip().rstrip(";")
        proposals.append(
            VillageLocationAliasProposal(
                alias_text=entry.term,
                parent_acs_code=acs_code,
                note=note,
                confidence=confidence,
                evidence=evidence,
            )
        )
    return tuple(proposals)


PROPOSED_VILLAGE_LOCATION_ALIASES: tuple[VillageLocationAliasProposal, ...] = (
    _load_proposed_aliases()
)

# Flagged uncertain — do NOT seed until reviewed. Documented as eval negatives
# in eval/corpus/village_matching.jsonl (Phase 2.5 / 3.3).
UNCERTAIN_VILLAGE_LOCATION_ALIAS_NOTES: tuple[str, ...] = (
    "وادي السلوقي / السلوقي: fuzzy hits Ouadi Es-Sitt (Chouf) or Slouqi (Baalbek); "
    "neither is the south-Lebanon Saluqi valley. No reliable ACS parent found.",
    "وادي الحجير / الحجير: no ACS village entry; fuzzy hits unrelated Ouadi Ed-Deir.",
    "الفوقا (bare): three-way tie Houmine / Nabatiyeh El-Faouka / Temnine — too ambiguous.",
    "بسطرة: unmatched; no ACS row found.",
    "بين الحنية و المنصوري (and similar between-X-and-Y): multi-location, not a single parent.",
    "Generic descriptor strip (محيط/أطراف/حرش/وادي) remains a separate pending task; "
    "only evidence-backed full phrases are seeded.",
)
