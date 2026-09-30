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
from app.llm.dtos import VillageRole, VillageRoleEntry
from app.llm.services.ollama_presence_gate_service import LOW_TEMPERATURE
from app.llm.services.tier1_segmenter import TextSegment

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
