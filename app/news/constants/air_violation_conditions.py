"""Canonical air-violation condition IDs.

Condition 45 is intentionally excluded. It is a Red Alert internal fallback for
unclassified air activity and should not be treated as a routable air violation.
"""

AIR_VIOLATION_CONDITION_IDS = frozenset({35, 36, 38})
AIR_VIOLATION_CONDITION_ID_TUPLE = tuple(sorted(AIR_VIOLATION_CONDITION_IDS))

