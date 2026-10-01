"""One place that turns an eligibility outcome into a raw-message status.

Every entry point that can create an air violation -- Red Alert, the Khabar
import, CNRS/general routing and the post-LLM backstop in the repository --
calls this, so a text that is rejected by one is rejected by all of them with
the same status and the same audit record.
"""
from __future__ import annotations

from typing import Any

from app.news.models import MessageStatus, RawMessage
from app.news.services.air_violations.air_violation_eligibility import (
    AirViolationOutcome,
    EligibilityResult,
)

#: Statuses that already represent a decision downstream. A collector retry
#: must never reopen a message whose incident reached a terminal state.
TERMINAL_STATUSES = frozenset({MessageStatus.materialized, MessageStatus.duplicate})

AUDIT_KEY_REROUTED = "air_violation_rerouted"
AUDIT_KEY_REJECTED = "air_violation_rejected"
AUDIT_KEY_HELD = "air_violation_held"

_AUDIT_KEYS: dict[AirViolationOutcome, str] = {
    AirViolationOutcome.belongs_in_incidents: AUDIT_KEY_REROUTED,
    AirViolationOutcome.reject_no_incident: AUDIT_KEY_REJECTED,
    AirViolationOutcome.hold_for_review: AUDIT_KEY_HELD,
}


def audit_entry(result: EligibilityResult, *, stage: str) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "reason": result.reason,
        "outcome": result.outcome.value,
        "matched_terms": list(result.matched_terms),
        "stage": stage,
    }
    if result.unmatched_location:
        entry["unmatched_location"] = result.unmatched_location
    return entry


def record_air_violation_outcome(
    message: RawMessage,
    result: EligibilityResult,
    *,
    stage: str,
) -> MessageStatus | None:
    """Write the audit trail and set the status this outcome demands.

    Returns the status that was set, or ``None`` when the message was left
    alone (already eligible, or already terminal downstream).

    A ``reject_no_incident`` result must not use the ``parsed`` reroute: that
    reroute exists to hand a kinetic report to the incident pipeline, and
    these rows are decided non-events. They become ``rejected`` and are never
    re-queued.
    """
    if result.eligible:
        return None

    outcome = result.outcome
    audit = dict(message.filter_result or {})
    audit[_AUDIT_KEYS[outcome]] = audit_entry(result, stage=stage)
    message.filter_result = audit

    if message.status in TERMINAL_STATUSES:
        return None

    if outcome is AirViolationOutcome.reject_no_incident:
        message.status = MessageStatus.rejected
        message.error_message = f"air_violation: {result.reason}"
        return MessageStatus.rejected

    if outcome is AirViolationOutcome.hold_for_review:
        message.status = MessageStatus.held_for_review
        message.error_message = f"air_violation: {result.reason}"
        return MessageStatus.held_for_review

    # 'parsed', not 'pending': writing the audit fills filter_result, and the
    # relevance stage only claims pending rows whose filter_result IS NULL, so
    # a pending row here is claimed by no stage at all. 'parsed' feeds
    # pre-dedup/extraction when there is no extraction yet, and matching when
    # there is.
    message.status = MessageStatus.parsed
    message.error_message = None
    return MessageStatus.parsed
