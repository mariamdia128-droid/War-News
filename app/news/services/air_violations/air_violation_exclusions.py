from __future__ import annotations

from dataclasses import dataclass

from app.news.services.air_violations.air_violation_eligibility import (
    evaluate_air_violation_text,
)


@dataclass(frozen=True)
class AirViolationExclusion:
    reason: str
    evidence_span: str


def air_violation_exclusion(text: str | None) -> AirViolationExclusion | None:
    result = evaluate_air_violation_text(text)
    if result.eligible:
        return None
    return AirViolationExclusion(
        reason=result.reason,
        evidence_span=", ".join(result.matched_terms) or (text or "")[:80].strip(),
    )
