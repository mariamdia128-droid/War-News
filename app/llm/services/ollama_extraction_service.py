from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.core.config import settings
from app.core.ollama_client import JsonObject, OllamaChatClient, OllamaChatMessage
from app.core.text_normalization import normalize_arabic_text
from app.core.llm_knowledge.loader import terms_by_category
from app.core.llm_knowledge.prompt_assembly import build_stage_system_prompt
from app.llm.dtos import (
    CasualtyCountEvidence,
    CasualtyScope,
    CasualtyTransition,
    ExtractionCasualties,
    ExtractionCategory,
    ExtractionCategoryKey,
    ExtractionResult,
    ExtractionSubEvent,
    VillageRole,
    VillageRoleEntry,
)
from app.llm.interfaces import ExtractionClassifierInterface
from app.llm.services.ollama_category_detail_service import OllamaCategoryDetailService
from app.llm.services.ollama_auth_failures import coerce_ollama_auth_failure
from app.llm.services.ollama_presence_gate_service import (
    LOW_TEMPERATURE,
    PRESENCE_GATE_RESPONSE_SCHEMA,
    OllamaPresenceGateService,
)
from app.llm.services.ollama_relevance_classifier_service import is_valid_reason_text
from app.news.services.incident_details.casualty_count_backstop import (
    apply_casualty_count_backstop,
)
from app.news.services.incident_details.casualty_scope_backstop import (
    validate_casualty_scope,
)
logger = logging.getLogger(__name__)

_DASH_ROUTE_RE = re.compile(
    r"طريق(?:\s+عام)?\s+"
    r"(?P<left>[\u0600-\u06ff][\u0600-\u06ff\s]{1,60}?)"
    r"\s*[-–—]\s*"
    r"(?P<right>[\u0600-\u06ff][\u0600-\u06ff\s]{1,60}?)"
    r"(?=$|[\n،؛.!؟])"
)
_ROUTE_AREA_PREFIXES = terms_by_category(
    "terminology/role_terms.yaml",
    "route_area_prefix",
) or ("مرج ",)

ALLOWED_EXTRACTION_CATEGORY_KEYS = frozenset(
    category.value for category in ExtractionCategoryKey
)

# Deprecated module-level aliases kept for scripts/docs that still name these
# constants. Runtime Tier-1 calls use build_stage_system_prompt() so matched
# terminology and situational rules can vary per message.
GENERAL_EXTRACTION_PROMPT = (
    Path(__file__).resolve().parents[2]
    / "core"
    / "llm_knowledge"
    / "rules"
    / "tier1_general_prompt.md"
).read_text(encoding="utf-8")

GENERAL_EXTRACTION_RESPONSE_SCHEMA: JsonObject = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_relevant": {"type": "boolean"},
        "village": {"type": ["array", "null"], "items": {"type": "string"}},
        "village_roles": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "village": {"type": "string"},
                    "role": {
                        "type": "string",
                        "enum": ["origin", "target"],
                    },
                    "deaths": {"type": ["integer", "null"], "minimum": 0},
                    "injuries": {"type": ["integer", "null"], "minimum": 0},
                    "evidence_span": {"type": ["string", "null"]},
                },
                "required": [
                    "village",
                    "role",
                    "deaths",
                    "injuries",
                    "evidence_span",
                ],
            },
        },
        "action_description": {"type": ["string", "null"]},
        "sub_events": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "action_description": {"type": ["string", "null"]},
                    "casualties": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "total_deaths": {"type": ["integer", "null"]},
                            "total_injuries": {"type": ["integer", "null"]},
                            "deaths": {"type": ["integer", "null"]},
                            "injuries": {"type": ["integer", "null"]},
                            "male_deaths": {"type": ["integer", "null"]},
                            "male_injuries": {"type": ["integer", "null"]},
                            "female_deaths": {"type": ["integer", "null"]},
                            "female_injuries": {"type": ["integer", "null"]},
                            "children_deaths": {"type": ["integer", "null"]},
                            "children_injuries": {"type": ["integer", "null"]},
                        },
                    },
                    "evidence_span": {"type": ["string", "null"]},
                    "casualty_evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "field": {
                                    "type": "string",
                                    "enum": [
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
                                    ],
                                },
                                "evidence_span": {"type": "string"},
                            },
                            "required": ["field", "evidence_span"],
                        },
                    },
                },
                "required": [
                    "action_description",
                    "casualties",
                    "evidence_span",
                    "casualty_evidence",
                ],
            },
        },
        "casualties": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "total_deaths": {"type": ["integer", "null"]},
                "total_injuries": {"type": ["integer", "null"]},
                "deaths": {"type": ["integer", "null"]},
                "injuries": {"type": ["integer", "null"]},
                "male_deaths": {"type": ["integer", "null"]},
                "male_injuries": {"type": ["integer", "null"]},
                "female_deaths": {"type": ["integer", "null"]},
                "female_injuries": {"type": ["integer", "null"]},
                "children_deaths": {"type": ["integer", "null"]},
                "children_injuries": {"type": ["integer", "null"]},
            },
        },
        "casualty_transitions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "from_status": {
                        "type": "string",
                        "enum": ["injured", "deceased"],
                    },
                    "to_status": {
                        "type": "string",
                        "enum": ["injured", "deceased"],
                    },
                    "count": {"type": "integer", "minimum": 1},
                },
                "required": ["from_status", "to_status", "count"],
            },
        },
        "casualty_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "field": {
                        "type": "string",
                        "enum": [
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
                        ],
                    },
                    "evidence_span": {"type": "string"},
                },
                "required": ["field", "evidence_span"],
            },
        },
        "casualty_scope": {
            "type": "string",
            "enum": [
                "per_village_exact",
                "bulletin_aggregate",
                "unspecified",
            ],
        },
        "casualty_scope_evidence": {"type": ["string", "null"]},
    },
    "required": [
        "is_relevant",
        "village",
        "village_roles",
        "action_description",
        "sub_events",
        "casualties",
        "casualty_transitions",
        "casualty_evidence",
        "casualty_scope",
        "casualty_scope_evidence",
    ],
}

COMBINED_TIER1_PROMPT = (
    Path(__file__).resolve().parents[2]
    / "core"
    / "llm_knowledge"
    / "rules"
    / "combined_tier1_prompt.md"
).read_text(encoding="utf-8")

COMBINED_TIER1_RESPONSE_SCHEMA: JsonObject = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "categories_present": PRESENCE_GATE_RESPONSE_SCHEMA["properties"]["categories_present"],  # type: ignore[index]
        "category_evidence": PRESENCE_GATE_RESPONSE_SCHEMA["properties"]["category_evidence"],  # type: ignore[index]
        "is_relevant": {"type": "boolean"},
        "village": {"type": ["array", "null"], "items": {"type": "string"}},
        "village_roles": GENERAL_EXTRACTION_RESPONSE_SCHEMA["properties"]["village_roles"],  # type: ignore[index]
        "action_description": {"type": ["string", "null"]},
        "sub_events": GENERAL_EXTRACTION_RESPONSE_SCHEMA["properties"]["sub_events"],  # type: ignore[index]
        "casualties": GENERAL_EXTRACTION_RESPONSE_SCHEMA["properties"]["casualties"],  # type: ignore[index]
        "casualty_transitions": GENERAL_EXTRACTION_RESPONSE_SCHEMA["properties"]["casualty_transitions"],  # type: ignore[index]
        "casualty_evidence": GENERAL_EXTRACTION_RESPONSE_SCHEMA["properties"]["casualty_evidence"],  # type: ignore[index]
        "casualty_scope": GENERAL_EXTRACTION_RESPONSE_SCHEMA["properties"]["casualty_scope"],  # type: ignore[index]
        "casualty_scope_evidence": GENERAL_EXTRACTION_RESPONSE_SCHEMA["properties"]["casualty_scope_evidence"],  # type: ignore[index]
    },
    "required": [
        "categories_present",
        "category_evidence",
        "is_relevant",
        "village",
        "village_roles",
        "action_description",
        "sub_events",
        "casualties",
        "casualty_transitions",
        "casualty_evidence",
        "casualty_scope",
        "casualty_scope_evidence",
    ],
}


class _RawExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    is_relevant: bool = True
    # Accept both old single-string responses and new array responses.
    village: list[str] | str | None = None
    village_roles: list[VillageRoleEntry] = Field(default_factory=list)
    action_description: str | None = None
    sub_events: list[ExtractionSubEvent] = Field(default_factory=list)
    casualties: ExtractionCasualties = Field(default_factory=ExtractionCasualties)
    casualty_transitions: list[CasualtyTransition] = Field(default_factory=list)
    casualty_evidence: list[CasualtyCountEvidence] = Field(default_factory=list)
    casualty_scope: CasualtyScope = CasualtyScope.unspecified
    casualty_scope_evidence: str | None = None

    @field_validator(
        "village_roles",
        "sub_events",
        "casualty_transitions",
        "casualty_evidence",
        mode="before",
    )
    @classmethod
    def _empty_list_for_none(cls, value: object) -> object:
        return [] if value is None else value


class OllamaExtractionService(ExtractionClassifierInterface):
    def __init__(
        self,
        client: OllamaChatClient,
        presence_gate: OllamaPresenceGateService | None = None,
        category_detail: OllamaCategoryDetailService | None = None,
        casualty_scope_aliases: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self.client = client
        self.presence_gate = presence_gate or OllamaPresenceGateService(client)
        self.category_detail = category_detail or OllamaCategoryDetailService(client)
        self.casualty_scope_aliases = casualty_scope_aliases or {}

    def extract_tier1(
        self,
        post_text: str,
        raw_message_id: int | None = None,
    ) -> ExtractionResult:
        if settings.tier1_use_combined_presence_extraction:
            return self._extract_tier1_combined(
                post_text,
                raw_message_id=raw_message_id,
            )

        categories_present = self.presence_gate.categories_present(
            post_text,
            raw_message_id=raw_message_id,
        )
        general_response = self._extract_general_fields(
            post_text,
            raw_message_id=raw_message_id,
        )
        return self._build_tier1_result(
            post_text=post_text,
            categories_present=categories_present,
            general_response=general_response,
            raw_message_id=raw_message_id,
        )

    def _extract_tier1_combined(
        self,
        post_text: str,
        raw_message_id: int | None = None,
    ) -> ExtractionResult:
        content = self.client.chat(
            [
                OllamaChatMessage(
                    role="system",
                    content=build_stage_system_prompt("combined_tier1", post_text),
                ),
                OllamaChatMessage(role="user", content=post_text),
            ],
            response_format=COMBINED_TIER1_RESPONSE_SCHEMA,
            temperature=LOW_TEMPERATURE,
        )
        try:
            payload = json.loads(content.strip())
        except json.JSONDecodeError as exc:
            logger.warning(
                "Malformed combined Tier1 response from model=%s "
                "for raw_message_id=%s: %s",
                self.client.model,
                raw_message_id,
                exc,
            )
            raise RuntimeError("Malformed combined Tier1 extraction response.") from exc

        presence_result = self.presence_gate.parse_presence_payload(
            payload,
            raw_message_id=raw_message_id,
            post_text=post_text,
        )
        general_payload = {
            key: payload.get(key)
            for key in (
                "is_relevant",
                "village",
                "village_roles",
                "action_description",
                "sub_events",
                "casualties",
                "casualty_transitions",
                "casualty_evidence",
                "casualty_scope",
                "casualty_scope_evidence",
            )
        }
        general_response = self._parse_general_response(
            json.dumps(general_payload, ensure_ascii=False),
            raw_message_id=raw_message_id,
        )
        return self._build_tier1_result(
            post_text=post_text,
            categories_present=presence_result.categories_present,
            general_response=general_response,
            raw_message_id=raw_message_id,
        )

    def _build_tier1_result(
        self,
        *,
        post_text: str,
        categories_present: list[ExtractionCategoryKey],
        general_response: _RawExtractionResponse,
        raw_message_id: int | None,
    ) -> ExtractionResult:
        casualties, casualty_evidence = apply_casualty_count_backstop(
            post_text,
            general_response.casualties,
            list(general_response.casualty_evidence),
            raw_message_id=raw_message_id,
        )
        categories: dict[ExtractionCategoryKey, ExtractionCategory] = {}
        self._inject_casualty_demographics_from_root(
            categories,
            casualties,
        )
        village_roles = self._validated_village_roles(
            general_response.village_roles,
            post_text=post_text,
            raw_message_id=raw_message_id,
        )
        villages = self._validated_village_list(
            general_response.village,
            raw_message_id=raw_message_id,
        )
        villages, village_roles = self._apply_dash_route_village_backstop(
            post_text,
            villages,
            village_roles,
        )
        scope, scope_evidence, scope_needs_review, scope_reason = (
            self._validated_casualty_scope(
                general_response,
                village_roles=village_roles,
                post_text=post_text,
                raw_message_id=raw_message_id,
            )
        )

        return ExtractionResult(
            is_relevant=general_response.is_relevant,
            village=villages,
            village_roles=village_roles,
            action_description=self._validated_text(
                general_response.action_description,
                field_name="action_description",
                raw_message_id=raw_message_id,
            ),
            sub_events=list(general_response.sub_events),
            categories=categories,
            casualties=casualties,
            casualty_evidence=casualty_evidence,
            casualty_transitions=list(general_response.casualty_transitions),
            casualty_scope=scope,
            casualty_scope_evidence=scope_evidence,
            casualty_scope_needs_review=scope_needs_review,
            casualty_scope_review_reason=scope_reason,
            presence_category_keys=list(categories_present),
            extraction_tier=1,
            model=self.client.model,
            extracted_at=datetime.now(timezone.utc),
        )

    def extract_tier2_details(
        self,
        post_text: str,
        presence_category_keys: list[ExtractionCategoryKey],
        *,
        root_casualties: ExtractionCasualties | None = None,
        raw_message_id: int | None = None,
    ) -> dict[ExtractionCategoryKey, ExtractionCategory]:
        """Run Tier-2 category detail extraction for keys detected in Tier 1."""
        if not presence_category_keys:
            return {}

        if settings.tier2_use_batched_category_detail:
            return self._extract_tier2_details_batched(
                post_text,
                presence_category_keys,
                root_casualties=root_casualties,
                raw_message_id=raw_message_id,
            )

        category_details: dict[str, ExtractionCategory] = {}
        failed_categories: list[str] = []
        for category_key in presence_category_keys:
            try:
                category_detail = self.category_detail.extract_detail(
                    post_text,
                    category_key=category_key,
                    raw_message_id=raw_message_id,
                )
            except Exception as exc:
                auth_failure = coerce_ollama_auth_failure(
                    exc,
                    stage="tier2_detail_fill",
                )
                if auth_failure is not None:
                    raise auth_failure from exc
                message = str(exc).strip()
                error = (
                    f"{type(exc).__name__}: {message}"
                    if message
                    else f"{type(exc).__name__} (no message)"
                )
                logger.exception(
                    "Failed to extract category detail category=%s "
                    "raw_message_id=%s error=%s",
                    category_key.value,
                    raw_message_id,
                    error,
                )
                failed_categories.append(category_key.value)
                continue

            if self._is_empty_category_detail(category_detail):
                logger.warning(
                    "Dropped empty category detail category=%s raw_message_id=%s",
                    category_key.value,
                    raw_message_id,
                )
                continue

            category_details[category_key.value] = category_detail

        if failed_categories:
            logger.error(
                "Tier2 category extraction incomplete raw_message_id=%s "
                "failed_categories=%s succeeded_categories=%s",
                raw_message_id,
                failed_categories,
                list(category_details.keys()),
            )

        return self._finalize_tier2_categories(
            category_details,
            root_casualties=root_casualties,
            raw_message_id=raw_message_id,
        )

    def _extract_tier2_details_batched(
        self,
        post_text: str,
        presence_category_keys: list[ExtractionCategoryKey],
        *,
        root_casualties: ExtractionCasualties | None,
        raw_message_id: int | None,
    ) -> dict[ExtractionCategoryKey, ExtractionCategory]:
        try:
            batched = self.category_detail.extract_details_batch(
                post_text,
                presence_category_keys,
                raw_message_id=raw_message_id,
            )
        except Exception as exc:
            auth_failure = coerce_ollama_auth_failure(
                exc,
                stage="tier2_detail_fill",
            )
            if auth_failure is not None:
                raise auth_failure from exc
            logger.exception(
                "Failed batched Tier2 category extraction raw_message_id=%s error=%s",
                raw_message_id,
                exc,
            )
            return {}

        category_details: dict[str, ExtractionCategory] = {}
        for category_key in presence_category_keys:
            category_detail = batched.get(category_key)
            if category_detail is None:
                logger.warning(
                    "Batched Tier2 missing category=%s raw_message_id=%s",
                    category_key.value,
                    raw_message_id,
                )
                continue
            if self._is_empty_category_detail(category_detail):
                logger.warning(
                    "Dropped empty batched category detail category=%s "
                    "raw_message_id=%s",
                    category_key.value,
                    raw_message_id,
                )
                continue
            category_details[category_key.value] = category_detail

        return self._finalize_tier2_categories(
            category_details,
            root_casualties=root_casualties,
            raw_message_id=raw_message_id,
        )

    def _finalize_tier2_categories(
        self,
        category_details: dict[str, ExtractionCategory],
        *,
        root_casualties: ExtractionCasualties | None,
        raw_message_id: int | None,
    ) -> dict[ExtractionCategoryKey, ExtractionCategory]:
        categories = self._validated_categories(
            category_details,
            raw_message_id=raw_message_id,
        )
        if root_casualties is not None:
            self._inject_casualty_demographics_from_root(categories, root_casualties)
        return categories

    def extract(
        self,
        post_text: str,
        raw_message_id: int | None = None,
    ) -> ExtractionResult:
        categories_present = self.presence_gate.categories_present(
            post_text,
            raw_message_id=raw_message_id,
        )
        general_response = self._extract_general_fields(
            post_text,
            raw_message_id=raw_message_id,
        )
        category_details: dict[str, ExtractionCategory] = {}
        failed_categories: list[str] = []
        for category_key in categories_present:
            try:
                category_detail = self.category_detail.extract_detail(
                    post_text,
                    category_key=category_key,
                    raw_message_id=raw_message_id,
                )
            except Exception as exc:
                auth_failure = coerce_ollama_auth_failure(
                    exc,
                    stage="tier2_detail_fill",
                )
                if auth_failure is not None:
                    raise auth_failure from exc
                message = str(exc).strip()
                error = (
                    f"{type(exc).__name__}: {message}"
                    if message
                    else f"{type(exc).__name__} (no message)"
                )
                logger.exception(
                    "Failed to extract category detail category=%s "
                    "raw_message_id=%s error=%s",
                    category_key.value,
                    raw_message_id,
                    error,
                )
                failed_categories.append(category_key.value)
                continue

            if self._is_empty_category_detail(category_detail):
                logger.warning(
                    "Dropped empty category detail category=%s raw_message_id=%s",
                    category_key.value,
                    raw_message_id,
                )
                continue

            category_details[category_key.value] = category_detail
        if failed_categories:
            logger.error(
                "Tier1 category extraction incomplete raw_message_id=%s "
                "failed_categories=%s succeeded_categories=%s",
                raw_message_id,
                failed_categories,
                list(category_details.keys()),
            )
        categories = self._validated_categories(
            category_details,
            raw_message_id=raw_message_id,
        )
        casualties, casualty_evidence = apply_casualty_count_backstop(
            post_text,
            general_response.casualties,
            list(general_response.casualty_evidence),
            raw_message_id=raw_message_id,
        )
        self._inject_casualty_demographics_from_root(
            categories,
            casualties,
        )
        village_roles = self._validated_village_roles(
            general_response.village_roles,
            post_text=post_text,
            raw_message_id=raw_message_id,
        )
        scope, scope_evidence, scope_needs_review, scope_reason = (
            self._validated_casualty_scope(
                general_response,
                village_roles=village_roles,
                post_text=post_text,
                raw_message_id=raw_message_id,
            )
        )

        return ExtractionResult(
            is_relevant=general_response.is_relevant,
            village=self._validated_village_list(
                general_response.village,
                raw_message_id=raw_message_id,
            ),
            village_roles=village_roles,
            action_description=self._validated_text(
                general_response.action_description,
                field_name="action_description",
                raw_message_id=raw_message_id,
            ),
            sub_events=list(general_response.sub_events),
            categories=categories,
            casualties=casualties,
            casualty_evidence=casualty_evidence,
            casualty_transitions=list(general_response.casualty_transitions),
            casualty_scope=scope,
            casualty_scope_evidence=scope_evidence,
            casualty_scope_needs_review=scope_needs_review,
            casualty_scope_review_reason=scope_reason,
            presence_category_keys=list(categories_present),
            extraction_tier=2,
            model=self.client.model,
            extracted_at=datetime.now(timezone.utc),
        )

    def _extract_general_fields(
        self,
        post_text: str,
        raw_message_id: int | None,
    ) -> _RawExtractionResponse:
        content = self.client.chat(
            [
                OllamaChatMessage(
                    role="system",
                    content=build_stage_system_prompt("tier1_extraction", post_text),
                ),
                OllamaChatMessage(role="user", content=post_text),
            ],
            response_format=GENERAL_EXTRACTION_RESPONSE_SCHEMA,
            temperature=LOW_TEMPERATURE,
        )
        return self._parse_general_response(content, raw_message_id=raw_message_id)

    def _parse_general_response(
        self,
        content: str,
        raw_message_id: int | None,
    ) -> _RawExtractionResponse:
        try:
            payload = json.loads(content.strip())
            response = _RawExtractionResponse.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            logger.warning(
                "Malformed extraction response from model=%s for raw_message_id=%s: %s",
                self.client.model,
                raw_message_id,
                exc,
            )
            raise RuntimeError("Malformed extraction response.") from exc

        # Normalise village to list[str] regardless of whether the model returned
        # a string (old-format or non-compliant) or an array.
        village_raw = response.village
        if isinstance(village_raw, str):
            parts = [p.strip() for p in village_raw.split(",") if p.strip()]
            village_norm: list[str] | None = parts if parts else None
        elif isinstance(village_raw, list):
            village_norm = village_raw if village_raw else None
        else:
            village_norm = None

        if village_norm is not response.village:
            response = response.model_copy(update={"village": village_norm})

        return response

    def _validated_categories(
        self,
        categories: dict[str, ExtractionCategory],
        raw_message_id: int | None,
    ) -> dict[ExtractionCategoryKey, ExtractionCategory]:
        validated: dict[ExtractionCategoryKey, ExtractionCategory] = {}
        for raw_key, raw_category in categories.items():
            if raw_key not in ALLOWED_EXTRACTION_CATEGORY_KEYS:
                logger.warning(
                    "Dropped invalid extraction category for raw_message_id=%s: %s",
                    raw_message_id,
                    raw_key,
                )
                continue

            category_key = ExtractionCategoryKey(raw_key)
            validated[category_key] = ExtractionCategory(
                did=raw_category.did,
                name=self._validated_text(
                    raw_category.name,
                    field_name=f"categories.{raw_key}.name",
                    raw_message_id=raw_message_id,
                ),
                casualties=raw_category.casualties,
                vehicles=raw_category.vehicles,
            )
        return validated

    def _has_populated_casualties(self, casualties: ExtractionCasualties) -> bool:
        return any(
            value is not None and value != 0
            for value in casualties.model_dump(mode="python").values()
        )

    def _inject_casualty_demographics_from_root(
        self,
        categories: dict[ExtractionCategoryKey, ExtractionCategory],
        root_casualties: ExtractionCasualties,
    ) -> None:
        if not self._has_populated_casualties(root_casualties):
            return

        category_key = ExtractionCategoryKey.casualty_demographics
        if category_key in categories:
            return

        categories[category_key] = ExtractionCategory(
            did=None,
            name=None,
            casualties=root_casualties,
        )

    def _is_empty_category_detail(self, category: ExtractionCategory) -> bool:
        if category.did is not None or category.name is not None:
            return False
        if category.vehicles is not None and any(
            value
            for value in category.vehicles.model_dump(mode="python").values()
            if value is not None and value is not False
        ):
            return False
        if category.casualties is None:
            return True
        return all(
            value is None
            for value in category.casualties.model_dump(mode="python").values()
        )

    def _validated_village_list(
        self,
        villages: list[str] | None,
        raw_message_id: int | None,
    ) -> list[str] | None:
        if not villages:
            return None
        validated: list[str] = []
        for entry in villages:
            if is_valid_reason_text(entry):
                validated.append(entry)
            else:
                logger.warning(
                    "Invalid village text from model=%s for raw_message_id=%s",
                    self.client.model,
                    raw_message_id,
                )
                logger.debug(
                    "Rejected village text from model=%s for raw_message_id=%s: %r",
                    self.client.model,
                    raw_message_id,
                    entry,
                )
        return validated if validated else None

    def _validated_village_roles(
        self,
        village_roles: list[VillageRoleEntry],
        post_text: str,
        raw_message_id: int | None,
    ) -> list[VillageRoleEntry]:
        validated: list[VillageRoleEntry] = []
        for entry in village_roles:
            if is_valid_reason_text(entry.village):
                evidence_span = self._validated_text(
                    entry.evidence_span,
                    field_name="village_roles.evidence_span",
                    raw_message_id=raw_message_id,
                )
                if evidence_span is not None and evidence_span not in post_text:
                    logger.warning(
                        "Dropped non-source village casualty evidence for "
                        "raw_message_id=%s village=%s",
                        raw_message_id,
                        entry.village,
                    )
                    evidence_span = None

                evidence = (
                    [
                        CasualtyCountEvidence(
                            field=field,
                            evidence_span=evidence_span,
                        )
                        for field, value in (
                            ("deaths", entry.deaths),
                            ("injuries", entry.injuries),
                        )
                        if value is not None and evidence_span is not None
                    ]
                    if evidence_span is not None
                    else []
                )
                village_casualties, _ = apply_casualty_count_backstop(
                    evidence_span or "",
                    ExtractionCasualties(
                        deaths=entry.deaths,
                        injuries=entry.injuries,
                    ),
                    evidence,
                    raw_message_id=raw_message_id,
                )
                validated.append(
                    entry.model_copy(
                        update={
                            "deaths": village_casualties.deaths,
                            "injuries": village_casualties.injuries,
                            "evidence_span": evidence_span,
                        }
                    )
                )
            else:
                logger.warning(
                    "Invalid village_roles.village text from model=%s for raw_message_id=%s",
                    self.client.model,
                    raw_message_id,
                )
                logger.debug(
                    "Rejected village_roles entry from model=%s for raw_message_id=%s: %r",
                    self.client.model,
                    raw_message_id,
                    entry.model_dump(mode="json"),
                )
        return validated

    @staticmethod
    def _apply_dash_route_village_backstop(
        post_text: str,
        villages: list[str] | None,
        village_roles: list[VillageRoleEntry],
    ) -> tuple[list[str] | None, list[VillageRoleEntry]]:
        """Recover both endpoints when a model drops one dash-joined route place."""
        match = _DASH_ROUTE_RE.search(post_text)
        if match is None:
            return villages, village_roles

        left = match.group("left").strip()
        for prefix in _ROUTE_AREA_PREFIXES:
            if left.startswith(prefix):
                left = left[len(prefix) :].strip()
                break
        right = match.group("right").strip()
        if not left or not right:
            return villages, village_roles

        existing_names = list(villages or [])
        existing_names.extend(entry.village for entry in village_roles)
        existing_norms = {
            normalize_arabic_text(name)
            for name in existing_names
            if normalize_arabic_text(name)
        }
        endpoint_norms = {
            normalize_arabic_text(left),
            normalize_arabic_text(right),
        }
        # Do not invent two locations from arbitrary dash punctuation. At least
        # one endpoint must already have been recognized by the model.
        if not existing_norms.intersection(endpoint_norms):
            return villages, village_roles

        merged_villages = list(villages or [])
        merged_norms = {
            normalize_arabic_text(name)
            for name in merged_villages
            if normalize_arabic_text(name)
        }
        merged_roles = list(village_roles)
        role_norms = {
            normalize_arabic_text(entry.village)
            for entry in merged_roles
            if normalize_arabic_text(entry.village)
        }
        for endpoint in (left, right):
            normalized = normalize_arabic_text(endpoint)
            if normalized not in merged_norms:
                merged_villages.append(endpoint)
                merged_norms.add(normalized)
            if normalized not in role_norms:
                merged_roles.append(
                    VillageRoleEntry(village=endpoint, role=VillageRole.target)
                )
                role_norms.add(normalized)
        return merged_villages, merged_roles

    def _validated_text(
        self,
        value: str | None,
        field_name: str,
        raw_message_id: int | None,
    ) -> str | None:
        if value is None:
            return None
        if is_valid_reason_text(value):
            return value

        logger.warning(
            "Invalid extraction text field=%s from model=%s for raw_message_id=%s",
            field_name,
            self.client.model,
            raw_message_id,
        )
        logger.debug(
            "Rejected extraction text field=%s from model=%s for raw_message_id=%s: %r",
            field_name,
            self.client.model,
            raw_message_id,
            value,
        )
        return None

    def _validated_source_span(
        self,
        value: str | None,
        *,
        post_text: str,
        field_name: str,
        raw_message_id: int | None,
    ) -> str | None:
        span = self._validated_text(
            value,
            field_name=field_name,
            raw_message_id=raw_message_id,
        )
        if span is None or span in post_text:
            return span
        logger.warning(
            "Dropped non-source extraction span field=%s raw_message_id=%s",
            field_name,
            raw_message_id,
        )
        return None

    def _validated_casualty_scope(
        self,
        response: _RawExtractionResponse,
        *,
        village_roles: list[VillageRoleEntry],
        post_text: str,
        raw_message_id: int | None,
    ) -> tuple[CasualtyScope, str | None, bool, str | None]:
        evidence = self._validated_source_span(
            response.casualty_scope_evidence,
            post_text=post_text,
            field_name="casualty_scope_evidence",
            raw_message_id=raw_message_id,
        )
        result = validate_casualty_scope(
            casualty_scope=response.casualty_scope,
            evidence=evidence,
            village_roles=village_roles,
            aliases_by_village=self.casualty_scope_aliases,
        )
        if result.plausible:
            return response.casualty_scope, evidence, False, None

        reason = (
            f"Unsupported casualty_scope={response.casualty_scope.value}: "
            f"evidence matched {result.village_count_in_evidence} target village(s)"
        )
        logger.warning("%s raw_message_id=%s", reason, raw_message_id)
        return CasualtyScope.unspecified, evidence, True, reason
