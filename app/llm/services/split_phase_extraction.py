"""Split-phase Tier 1 building blocks (TIER1_SPLIT_PHASES_ENABLED).

Each raw message is cut into news items (``tier1_segmenter``) and every item
gets small single-purpose LLM calls: an event call (relevance, villages,
roles, action) and, only when casualties are present in that item, a
casualty call. Everything else (presence assignment, scope, root totals) is
decided in code here and in ``OllamaExtractionService._extract_tier1_split``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.core.llm_knowledge.prompt_assembly import build_stage_system_prompt
from app.core.ollama_client import JsonObject, OllamaChatClient, OllamaChatMessage
from app.core.text_normalization import normalize_arabic_text
from app.llm.dtos import (
    CasualtyCountEvidence,
    CasualtyTransition,
    CasualtyTransitionStatus,
    ExtractionCasualties,
    ExtractionCategoryKey,
    VillageRole,
    VillageRoleEntry,
)
from app.llm.services.ollama_presence_gate_service import (
    LOW_TEMPERATURE,
    OllamaPresenceGateService,
    PresenceGateResult,
)
from app.llm.services.tier1_segmenter import TextSegment
from app.news.services.incident_details.casualty_count_backstop import (
    apply_casualty_count_backstop,
)
from app.news.services.incident_details.casualty_text import (
    find_count_mentions,
    find_explicit_none,
    has_casualty_wording,
)

logger = logging.getLogger(__name__)

SEGMENT_EVENT_RESPONSE_SCHEMA: JsonObject = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_relevant": {"type": "boolean"},
        "villages": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string", "enum": ["origin", "target"]},
                    "qualifier_text": {"type": ["string", "null"]},
                },
                "required": ["name", "role", "qualifier_text"],
            },
        },
        "action_description": {"type": ["string", "null"]},
    },
    "required": ["is_relevant", "villages", "action_description"],
}


class _RawSegmentVillage(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    name: str
    role: VillageRole = VillageRole.target
    qualifier_text: str | None = None


class _RawSegmentEvent(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    is_relevant: bool = True
    villages: list[_RawSegmentVillage] = Field(default_factory=list)
    action_description: str | None = None

    @field_validator("villages", mode="before")
    @classmethod
    def _empty_list_for_none(cls, value: object) -> object:
        return [] if value is None else value


@dataclass(frozen=True)
class SegmentEvent:
    is_relevant: bool
    village_roles: list[VillageRoleEntry] = field(default_factory=list)
    action_description: str | None = None

    @property
    def target_names(self) -> list[str]:
        return [entry.village for entry in self.village_roles if entry.role == VillageRole.target]


def segment_user_content(segment: TextSegment) -> str:
    """User message for one segment; a list header is context only."""
    if segment.header and segment.header not in segment.text:
        return f"سياق: {segment.header}\n\nالبند:\n{segment.text}"
    return segment.text


def extract_segment_event(
    client: OllamaChatClient,
    segment: TextSegment,
    *,
    raw_message_id: int | None,
) -> SegmentEvent:
    """Relevance, villages/roles and action for one segment (no numbers)."""
    content = client.chat(
        [
            OllamaChatMessage(
                role="system",
                content=build_stage_system_prompt("tier1_event", segment.text),
            ),
            OllamaChatMessage(role="user", content=segment_user_content(segment)),
        ],
        response_format=SEGMENT_EVENT_RESPONSE_SCHEMA,
        temperature=LOW_TEMPERATURE,
    )
    return parse_segment_event(
        content,
        model=client.model,
        segment_index=segment.index,
        raw_message_id=raw_message_id,
    )


def parse_segment_event(
    content: str,
    *,
    model: str | None,
    segment_index: int,
    raw_message_id: int | None,
) -> SegmentEvent:
    try:
        response = _RawSegmentEvent.model_validate(json.loads(content.strip()))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        logger.warning(
            "Malformed segment event response from model=%s raw_message_id=%s "
            "segment=%s: %s",
            model,
            raw_message_id,
            segment_index,
            exc,
        )
        raise RuntimeError("Malformed segment event response.") from exc

    roles: list[VillageRoleEntry] = []
    seen: set[tuple[str, VillageRole]] = set()
    for village in response.villages:
        name = village.name.strip()
        if not name or (name, village.role) in seen:
            continue
        seen.add((name, village.role))
        qualifier = (village.qualifier_text or "").strip() or None
        roles.append(
            VillageRoleEntry(village=name, role=village.role, qualifier_text=qualifier)
        )
    return SegmentEvent(
        is_relevant=response.is_relevant,
        village_roles=roles,
        action_description=(response.action_description or "").strip() or None,
    )


# --- Casualty call ------------------------------------------------------------

_SEGMENT_CASUALTY_FIELDS = (
    "deaths",
    "injuries",
    "male_deaths",
    "male_injuries",
    "female_deaths",
    "female_injuries",
    "children_deaths",
    "children_injuries",
)

SEGMENT_CASUALTY_RESPONSE_SCHEMA: JsonObject = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "casualties": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                name: {"type": ["integer", "null"], "minimum": 0}
                for name in _SEGMENT_CASUALTY_FIELDS
            },
            "required": list(_SEGMENT_CASUALTY_FIELDS),
        },
        "casualty_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "field": {"type": "string", "enum": list(_SEGMENT_CASUALTY_FIELDS)},
                    "evidence_span": {"type": "string"},
                },
                "required": ["field", "evidence_span"],
            },
        },
        "village_casualties": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "village": {"type": "string"},
                    "deaths": {"type": ["integer", "null"], "minimum": 0},
                    "injuries": {"type": ["integer", "null"], "minimum": 0},
                    "evidence_span": {"type": "string"},
                },
                "required": ["village", "deaths", "injuries", "evidence_span"],
            },
        },
        "casualty_transitions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "from_status": {"type": "string", "enum": ["injured", "deceased"]},
                    "to_status": {"type": "string", "enum": ["injured", "deceased"]},
                    "count": {"type": "integer", "minimum": 1},
                    "evidence_span": {"type": "string"},
                },
                "required": ["from_status", "to_status", "count", "evidence_span"],
            },
        },
    },
    "required": [
        "casualties",
        "casualty_evidence",
        "village_casualties",
        "casualty_transitions",
    ],
}


class _RawVillageCasualty(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    village: str
    deaths: int | None = None
    injuries: int | None = None
    evidence_span: str | None = None


class _RawTransition(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    from_status: CasualtyTransitionStatus
    to_status: CasualtyTransitionStatus
    count: int = Field(ge=1)
    evidence_span: str | None = None


class _RawSegmentCasualties(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    casualties: ExtractionCasualties = Field(default_factory=ExtractionCasualties)
    casualty_evidence: list[CasualtyCountEvidence] = Field(default_factory=list)
    village_casualties: list[_RawVillageCasualty] = Field(default_factory=list)
    casualty_transitions: list[_RawTransition] = Field(default_factory=list)

    @field_validator(
        "casualty_evidence",
        "village_casualties",
        "casualty_transitions",
        mode="before",
    )
    @classmethod
    def _empty_list_for_none(cls, value: object) -> object:
        return [] if value is None else value

    @field_validator("casualties", mode="before")
    @classmethod
    def _empty_casualties_for_none(cls, value: object) -> object:
        return {} if value is None else value


@dataclass(frozen=True)
class SegmentCasualties:
    """Validated casualty numbers for one segment; every count is grounded."""

    casualties: ExtractionCasualties = field(default_factory=ExtractionCasualties)
    casualty_evidence: list[CasualtyCountEvidence] = field(default_factory=list)
    # Target villages with their own explicit count inside a multi-village item.
    village_casualties: list[VillageRoleEntry] = field(default_factory=list)
    transitions: list[CasualtyTransition] = field(default_factory=list)

    def has_counts(self) -> bool:
        return (
            any(
                value is not None
                for value in self.casualties.model_dump(mode="python").values()
            )
            or bool(self.village_casualties)
            or bool(self.transitions)
        )


def segment_has_casualty_language(text: str) -> bool:
    """Keyword pre-check for casualty_demographics in one segment."""
    return bool(
        find_count_mentions(text)
        or has_casualty_wording(text, "deaths")
        or has_casualty_wording(text, "injuries")
        or find_explicit_none(text, "deaths")
        or find_explicit_none(text, "injuries")
    )


def extract_segment_casualties(
    client: OllamaChatClient,
    segment: TextSegment,
    *,
    villages: list[str],
    raw_message_id: int | None,
) -> SegmentCasualties:
    """Casualty numbers for one segment; call only when casualties are present."""
    village_line = "، ".join(villages) if villages else "غير محددة"
    content = client.chat(
        [
            OllamaChatMessage(
                role="system",
                content=build_stage_system_prompt("tier1_casualty", segment.text),
            ),
            OllamaChatMessage(
                role="user",
                content=(
                    f"البلدات المستهدفة: {village_line}\n\n"
                    f"البند:\n{segment_user_content(segment)}"
                ),
            ),
        ],
        response_format=SEGMENT_CASUALTY_RESPONSE_SCHEMA,
        temperature=LOW_TEMPERATURE,
    )
    return parse_segment_casualties(
        content,
        segment_text=segment.text,
        villages=villages,
        model=client.model,
        segment_index=segment.index,
        raw_message_id=raw_message_id,
    )


def parse_segment_casualties(
    content: str,
    *,
    segment_text: str,
    villages: list[str],
    model: str | None,
    segment_index: int,
    raw_message_id: int | None,
) -> SegmentCasualties:
    try:
        response = _RawSegmentCasualties.model_validate(json.loads(content.strip()))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        logger.warning(
            "Malformed segment casualty response from model=%s raw_message_id=%s "
            "segment=%s: %s",
            model,
            raw_message_id,
            segment_index,
            exc,
        )
        raise RuntimeError("Malformed segment casualty response.") from exc

    # Same count backstop as the whole-message path, run on the segment only:
    # a number stated in another item can never validate this item's count.
    casualties, evidence = apply_casualty_count_backstop(
        segment_text,
        response.casualties,
        list(response.casualty_evidence),
        raw_message_id=raw_message_id,
    )

    known = {_name_key(name): name for name in villages}
    village_casualties: list[VillageRoleEntry] = []
    for item in response.village_casualties:
        name = known.get(_name_key(item.village))
        span = (item.evidence_span or "").strip()
        if name is None or not span or span not in segment_text:
            logger.warning(
                "Dropped ungrounded segment village casualty raw_message_id=%s "
                "segment=%s village=%s",
                raw_message_id,
                segment_index,
                item.village,
            )
            continue
        counts, _ = apply_casualty_count_backstop(
            span,
            ExtractionCasualties(deaths=item.deaths, injuries=item.injuries),
            [
                CasualtyCountEvidence(field=field_name, evidence_span=span)
                for field_name, value in (
                    ("deaths", item.deaths),
                    ("injuries", item.injuries),
                )
                if value is not None
            ],
            raw_message_id=raw_message_id,
        )
        if counts.deaths is None and counts.injuries is None:
            continue
        village_casualties.append(
            VillageRoleEntry(
                village=name,
                role=VillageRole.target,
                deaths=counts.deaths,
                injuries=counts.injuries,
                evidence_span=span,
            )
        )

    transitions: list[CasualtyTransition] = []
    for item in response.casualty_transitions:
        span = (item.evidence_span or "").strip()
        if not span or span not in segment_text:
            logger.warning(
                "Dropped ungrounded segment casualty transition raw_message_id=%s "
                "segment=%s",
                raw_message_id,
                segment_index,
            )
            continue
        transitions.append(
            CasualtyTransition(
                from_status=item.from_status,
                to_status=item.to_status,
                count=item.count,
            )
        )

    return SegmentCasualties(
        casualties=casualties,
        casualty_evidence=evidence,
        village_casualties=village_casualties,
        transitions=transitions,
    )


def _name_key(name: str) -> str:
    return normalize_arabic_text(name or "", compact=True).lower()


# --- Presence assignment ------------------------------------------------------

# Categories with an existing deterministic term list may legitimately sit in
# several segments at once (two cars hit in two items).
_KEYWORD_PLACEABLE = frozenset(
    {
        ExtractionCategoryKey.vehicles,
        ExtractionCategoryKey.emergency_civil_defense,
    }
)


@dataclass
class SegmentPresence:
    """Which categories each segment carries, decided from one gate call."""

    per_segment: list[list[ExtractionCategoryKey]]
    # Present in the message but not placeable in any single segment.
    unplaced: list[ExtractionCategoryKey] = field(default_factory=list)
    segment_gate_calls: int = 0


def _span_in(span: str, text: str) -> bool:
    if not span:
        return False
    if span in text:
        return True
    folded_span = normalize_arabic_text(span, compact=True)
    return bool(folded_span) and folded_span in normalize_arabic_text(text, compact=True)


def _keyword_holders(
    gate: OllamaPresenceGateService,
    key: ExtractionCategoryKey,
    segments: list[TextSegment],
    candidates: list[int],
) -> list[int]:
    """Segments matched by the gate's existing term lists, where one exists."""
    if key == ExtractionCategoryKey.vehicles:
        return [
            i for i in candidates if gate._has_vehicle_language("", segments[i].text)
        ]
    if key == ExtractionCategoryKey.emergency_civil_defense:
        return [
            i
            for i in candidates
            if gate._has_civil_defense_organization_language(segments[i].text)
        ]
    return []


def assign_presence(
    gate: OllamaPresenceGateService,
    gate_result: PresenceGateResult,
    segments: list[TextSegment],
    *,
    eligible: list[int],
    raw_message_id: int | None,
) -> SegmentPresence:
    """Assign whole-message presence keys to the segments that hold them.

    ``gate_result`` comes from one gate call on the whole message. Each key
    goes to the segment containing its evidence span; the existing vehicle and
    civil-defense term lists break ties. Only keys that still cannot be placed
    trigger a per-segment gate call (at most one per segment).

    casualty_demographics is decided per segment by the casualty keyword
    pre-check (or the gate's span): the current path extracts casualties
    whatever the gate says, so the split path must not depend on it either.
    """
    per_segment: list[list[ExtractionCategoryKey]] = [[] for _ in segments]
    evidence = {
        item.category_key: (item.evidence_span or "").strip()
        for item in gate_result.category_evidence
    }
    pending: dict[ExtractionCategoryKey, list[int]] = {}

    for index in eligible:
        if segment_has_casualty_language(segments[index].text):
            per_segment[index].append(ExtractionCategoryKey.casualty_demographics)

    for key in gate_result.categories_present:
        span = evidence.get(key, "")
        if key == ExtractionCategoryKey.casualty_demographics:
            for index in eligible:
                if key not in per_segment[index] and _span_in(span, segments[index].text):
                    per_segment[index].append(key)
            continue
        if len(segments) == 1:
            if eligible:
                per_segment[0].append(key)
            continue
        holders = [i for i in eligible if _span_in(span, segments[i].text)]
        if not holders and any(
            _span_in(span, segments[i].text)
            for i in range(len(segments))
            if i not in eligible
        ):
            # The evidence sits in an item the event call judged irrelevant.
            logger.info(
                "split presence dropped category=%s held by an irrelevant segment "
                "raw_message_id=%s",
                key.value,
                raw_message_id,
            )
            continue
        if len(holders) != 1 and key in _KEYWORD_PLACEABLE:
            keyword = _keyword_holders(gate, key, segments, holders or list(eligible))
            if keyword:
                holders = keyword
                for index in holders:
                    per_segment[index].append(key)
                continue
        if len(holders) == 1:
            per_segment[holders[0]].append(key)
            continue
        pending[key] = holders or list(eligible)

    calls = 0
    unplaced: list[ExtractionCategoryKey] = []
    if pending:
        asked = sorted({index for indexes in pending.values() for index in indexes})
        found: dict[int, set[ExtractionCategoryKey]] = {}
        for index in asked:
            calls += 1
            result = gate.evaluate(segments[index].text, raw_message_id=raw_message_id)
            found[index] = set(result.categories_present)
        for key, candidates in pending.items():
            holders = [index for index in candidates if key in found.get(index, set())]
            if not holders:
                unplaced.append(key)
                logger.warning(
                    "split presence could not place category=%s raw_message_id=%s",
                    key.value,
                    raw_message_id,
                )
                continue
            for index in holders:
                per_segment[index].append(key)

    return SegmentPresence(
        per_segment=per_segment,
        unplaced=unplaced,
        segment_gate_calls=calls,
    )


# --- Assembler ----------------------------------------------------------------

SPLIT_MIXED_SCOPE_REVIEW_REASON = (
    "Split extraction: a bulletin-wide casualty toll sits next to other item tolls"
)

_ROOT_SUM_FIELDS = (
    "total_deaths",
    "total_injuries",
    "deaths",
    "injuries",
    "male_deaths",
    "male_injuries",
    "female_deaths",
    "female_injuries",
    "children_deaths",
    "children_injuries",
)


@dataclass(frozen=True)
class SplitAssembly:
    """Whole-message fields built from the per-segment results."""

    # Shaped like the general Tier 1 response (_RawExtractionResponse).
    payload: dict
    # Presence keys for the root, in first-seen order (segments, then unplaced).
    root_category_keys: list[ExtractionCategoryKey]
    scope_review_reason: str | None = None


def _add(left: int | None, right: int | None) -> int | None:
    if left is None:
        return right
    if right is None:
        return left
    return left + right


def _unit_casualties(
    targets: list[str],
    casualties: SegmentCasualties | None,
) -> tuple[ExtractionCasualties, list[CasualtyCountEvidence], str]:
    """(casualties, evidence, kind) for one item.

    kind is "none" (no counts), "exact" (one target, or per-village counts),
    "aggregate" (one toll shared by several targets) or "unattributed".
    """
    if casualties is None:
        return ExtractionCasualties(), [], "none"
    counts = casualties.casualties
    evidence = list(casualties.casualty_evidence)
    if counts.deaths is None and counts.injuries is None and casualties.village_casualties:
        deaths = injuries = None
        for entry in casualties.village_casualties:
            deaths = _add(deaths, entry.deaths)
            injuries = _add(injuries, entry.injuries)
        counts = counts.model_copy(update={"deaths": deaths, "injuries": injuries})
    if counts.deaths is None and counts.injuries is None:
        return counts, evidence, "none"
    if len(targets) >= 2 and not casualties.village_casualties:
        # One shared toll for several villages: totals only, like the
        # whole-message prompt's bulletin_aggregate convention.
        aggregate = counts.model_copy(
            update={
                "total_deaths": counts.deaths,
                "total_injuries": counts.injuries,
                "deaths": None,
                "injuries": None,
            }
        )
        renamed = [
            item.model_copy(update={"field": f"total_{item.field}"})
            if item.field in {"deaths", "injuries"}
            else item
            for item in evidence
        ]
        return aggregate, renamed, "aggregate"
    exact = counts.model_copy(
        update={"total_deaths": counts.deaths, "total_injuries": counts.injuries}
    )
    kind = "exact" if targets else "unattributed"
    return exact, evidence, kind


def _unit_locations(
    event: SegmentEvent,
    casualties: SegmentCasualties | None,
    unit: ExtractionCasualties,
    kind: str,
    segment_text: str,
) -> list[VillageRoleEntry]:
    per_village = {
        _name_key(entry.village): entry
        for entry in (casualties.village_casualties if casualties else [])
    }
    locations: list[VillageRoleEntry] = []
    for entry in event.village_roles:
        if entry.role != VillageRole.target:
            locations.append(entry)
            continue
        own = per_village.get(_name_key(entry.village))
        if own is not None:
            entry = entry.model_copy(
                update={
                    "deaths": own.deaths,
                    "injuries": own.injuries,
                    "evidence_span": own.evidence_span,
                }
            )
        elif kind == "exact" and len(event.target_names) == 1:
            # The item's own toll belongs to its only target; the item text is
            # the literal span (it holds the village name and the numbers).
            entry = entry.model_copy(
                update={
                    "deaths": unit.deaths,
                    "injuries": unit.injuries,
                    "evidence_span": segment_text,
                }
            )
        locations.append(entry)
    return locations


def assemble_split_payload(
    segments: list[TextSegment],
    events: list[SegmentEvent | None],
    *,
    eligible: list[int],
    casualties_by_segment: dict[int, SegmentCasualties],
    presence: SegmentPresence,
) -> SplitAssembly:
    """Build the whole-message Tier 1 fields from per-item results (no LLM).

    * one sub_event per relevant item when there are two or more;
    * root casualties are the sum over items (never re-added on top of
      entity counts: entities are only filled in Tier 2);
    * casualty_scope decided in code: every item with numbers has its own
      village → per_village_exact; exactly one item with a shared toll over
      several villages → bulletin_aggregate; anything else → unspecified
      (a mix is flagged for review).
    """
    root_counts: dict[str, int | None] = dict.fromkeys(_ROOT_SUM_FIELDS)
    root_evidence: list[CasualtyCountEvidence] = []
    root_roles: dict[tuple[str, VillageRole], VillageRoleEntry] = {}
    villages: list[str] = []
    transitions: list[dict] = []
    sub_events: list[dict] = []
    kinds: list[tuple[str, int]] = []
    root_keys: list[ExtractionCategoryKey] = []
    action: str | None = None

    for index in eligible:
        segment = segments[index]
        event = events[index]
        if event is None:
            continue
        casualties = casualties_by_segment.get(index)
        unit, evidence, kind = _unit_casualties(event.target_names, casualties)
        if kind != "none":
            kinds.append((kind, index))
        locations = _unit_locations(event, casualties, unit, kind, segment.text)
        keys = list(presence.per_segment[index])
        if ExtractionCategoryKey.casualty_demographics in keys and (
            casualties is None or not casualties.has_counts()
        ):
            keys.remove(ExtractionCategoryKey.casualty_demographics)
        for key in keys:
            if key not in root_keys:
                root_keys.append(key)

        for name in _ROOT_SUM_FIELDS:
            root_counts[name] = _add(root_counts[name], getattr(unit, name))
        root_evidence.extend(evidence)
        for entry in locations:
            role_key = (_name_key(entry.village), entry.role)
            if entry.village not in villages:
                villages.append(entry.village)
            existing = root_roles.get(role_key)
            if existing is None:
                root_roles[role_key] = entry
                continue
            # The same village hit in two items: its counts add up.
            root_roles[role_key] = existing.model_copy(
                update={
                    "deaths": _add(existing.deaths, entry.deaths),
                    "injuries": _add(existing.injuries, entry.injuries),
                    "evidence_span": existing.evidence_span or entry.evidence_span,
                }
            )
        if casualties is not None:
            transitions.extend(
                item.model_dump(mode="json") for item in casualties.transitions
            )
        action = action or event.action_description
        sub_events.append(
            {
                "locations": [entry.model_dump(mode="json") for entry in locations],
                "action_text": event.action_description,
                "casualties": unit.model_dump(mode="json"),
                "evidence_span": segment.text,
                "casualty_evidence": [item.model_dump(mode="json") for item in evidence],
                "segment_index": segment.index,
                "segment_span": [segment.start, segment.end],
                "presence_category_keys": [key.value for key in keys],
            }
        )

    for key in presence.unplaced:
        if key not in root_keys:
            root_keys.append(key)

    scope, scope_evidence, review_reason = _decide_scope(kinds, segments)
    roles = list(root_roles.values())
    payload = {
        "is_relevant": bool(sub_events),
        "village": villages or None,
        "village_roles": [entry.model_dump(mode="json") for entry in roles],
        "action_description": action,
        # A single item keeps the current single-event shape (no sub_events).
        "sub_events": sub_events if len(sub_events) >= 2 else [],
        "casualties": root_counts,
        "casualty_transitions": transitions,
        "casualty_evidence": [item.model_dump(mode="json") for item in root_evidence],
        "casualty_scope": scope,
        "casualty_scope_evidence": scope_evidence,
    }
    return SplitAssembly(
        payload=payload,
        root_category_keys=root_keys,
        scope_review_reason=review_reason,
    )


def _decide_scope(
    kinds: list[tuple[str, int]],
    segments: list[TextSegment],
) -> tuple[str, str | None, str | None]:
    if not kinds:
        return "unspecified", None, None
    names = {kind for kind, _ in kinds}
    if names == {"exact"}:
        return "per_village_exact", segments[kinds[0][1]].text, None
    if names == {"aggregate"} and len(kinds) == 1:
        return "bulletin_aggregate", segments[kinds[0][1]].text, None
    if "aggregate" in names:
        # A shared toll next to other tolls cannot be one bulletin group.
        return "unspecified", None, SPLIT_MIXED_SCOPE_REVIEW_REASON
    return "unspecified", None, None
