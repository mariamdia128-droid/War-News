"""Pure guard against copying bulletin totals onto a single-location incident."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CasualtyMergeDecision:
    suppress: bool
    reason: str | None = None


def guard_casualty_merge(
    *,
    incident_village_id: int | None,
    target_location_count: int,
    casualty_scope: str | None,
    incoming_status: str | None,
    village_matches: list[dict[str, Any]] | None,
) -> CasualtyMergeDecision:
    """Suppress aggregate counts unless attribution explicitly owns this row."""
    own_attribution = any(
        item.get("village_role", "target") == "target"
        and item.get("matched_village_id") == incident_village_id
        and any(
            isinstance(item.get(field), int) and not isinstance(item.get(field), bool)
            for field in ("deaths", "injuries", "total_deaths", "total_injuries")
        )
        for item in (village_matches or [])
    )
    aggregate = (
        casualty_scope == "bulletin_aggregate"
        or incoming_status == "aggregate_only"
        or target_location_count >= 2
    )
    if aggregate and not own_attribution:
        return CasualtyMergeDecision(True, "aggregate_casualties_suppressed")
    return CasualtyMergeDecision(False)
