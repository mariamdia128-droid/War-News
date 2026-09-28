"""Decide whether a parked raw message can go back through the pipeline.

Pure classification: no database access, no LLM. The requeue script uses it
to pick the stage a message should restart from; permanent rejections
(exact-hash duplicates, air violations, irrelevant posts) are never requeued.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.text_normalization import normalize_arabic_text
from app.llm.services.transient_llm_errors import TRANSIENT_LLM_ERROR_MARKERS
from app.news.models import MessageStatus
from app.news.services.dedup.fast_path_eligibility import (
    ERROR_AIR_VIOLATION,
    ERROR_EXACT_HASH,
    ERROR_NO_VILLAGE,
    ERROR_UNMATCHED_CONDITION,
    ERROR_UNMATERIALIZABLE,
    HELD_UNMATCHED_PLACE,
)

PLAN_REMATCH = "rematch"
PLAN_REEXTRACT = "reextract"
PLAN_SKIP = "skip"

REQUEUEABLE_STATUSES = frozenset(
    {MessageStatus.error.value, MessageStatus.held_for_review.value}
)
_REMATCHABLE_REASONS = (
    ERROR_UNMATCHED_CONDITION,
    ERROR_NO_VILLAGE,
    ERROR_UNMATERIALIZABLE,
    HELD_UNMATCHED_PLACE,
)
_PERMANENT_REASONS = {
    ERROR_EXACT_HASH: "exact_hash_duplicate",
    ERROR_AIR_VIOLATION: "air_violation",
    "red_alert: routed to air_violations": "air_violation",
}
_EXTRACTION_RETRY_CAP_PREFIX = "extraction: exceeded max retries"
# A hostile actor or military action named in the text. Many "unmatched
# condition" rows are civilian fires/accidents (e.g. 285 «حريق داخل منزل في
# البحصة – طرابلس») whose condition was withheld on purpose; re-matching them
# would now land on the Unclassified fallback and create false incidents.
_CONFLICT_EVIDENCE = re.compile(
    normalize_arabic_text(
        r"غار|قصف|اسرائيل|العدو|معادي|معاديه|صهيون|احتلال|مسير|ميركافا|دباب"
        r"|تمشيط|تفجير|استهداف|استهدف|شهيد|جريح|انفجار|قذيف|جرف|توغل"
    )
)


def has_conflict_evidence(text: str | None) -> bool:
    return bool(_CONFLICT_EVIDENCE.search(normalize_arabic_text(text or "")))


@dataclass(frozen=True)
class RequeueDecision:
    plan: str
    reason_group: str
    skip_reason: str | None = None


def reason_group(error_message: str | None) -> str:
    """Collapse numbers so similar error texts group together."""
    text = (error_message or "<none>").strip()
    return re.sub(r"\d+", "#", text)[:120]


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _status_value(status: Any) -> str:
    return str(getattr(status, "value", status))


def extraction_names_a_place(extraction: dict[str, Any] | None) -> bool:
    if not extraction:
        return False
    villages = extraction.get("village")
    if isinstance(villages, str) and villages.strip():
        return True
    if isinstance(villages, list) and any(str(item).strip() for item in villages):
        return True
    for role in extraction.get("village_roles") or ():
        if str(_get(role, "village", "")).strip():
            return True
    for event in extraction.get("sub_events") or ():
        for location in _get(event, "locations", ()) or ():
            if str(_get(location, "village", "")).strip():
                return True
    return False


def _is_transient(error_message: str) -> bool:
    lowered = error_message.lower()
    return any(marker in lowered for marker in TRANSIENT_LLM_ERROR_MARKERS)


def classify_errored_message(
    message: Any,
    *,
    has_live_incident: bool,
    include_no_place_reextract: bool = False,
) -> RequeueDecision:
    error_message = str(_get(message, "error_message") or "")
    group = reason_group(error_message)

    def skip(why: str) -> RequeueDecision:
        return RequeueDecision(PLAN_SKIP, group, why)

    if _status_value(_get(message, "status")) not in REQUEUEABLE_STATUSES:
        return skip("not_errored_or_held")
    if _get(message, "duplicate_of_id") is not None:
        return skip("duplicate_of_other_message")
    if has_live_incident:
        return skip("has_live_incident")
    verdict = (_get(message, "filter_result") or {}).get("verdict")
    if verdict not in (None, "relevant"):
        return skip("not_relevant")
    for prefix, why in _PERMANENT_REASONS.items():
        if error_message.startswith(prefix):
            return skip(why)

    extraction = _get(message, "extraction_result")
    if extraction is None:
        if _is_transient(error_message) or error_message.startswith(
            _EXTRACTION_RETRY_CAP_PREFIX
        ):
            return RequeueDecision(PLAN_REEXTRACT, group)
        return skip("extraction_failed_non_transient")
    if extraction.get("is_relevant") is False:
        return skip("extraction_marked_irrelevant")

    if error_message.startswith(_REMATCHABLE_REASONS):
        if not has_conflict_evidence(_get(message, "raw_text")):
            return skip("no_conflict_evidence")
        if extraction_names_a_place(extraction):
            return RequeueDecision(PLAN_REMATCH, group)
        if include_no_place_reextract:
            return RequeueDecision(PLAN_REEXTRACT, group)
        return skip("no_place_extracted")
    return skip("unknown_reason")
