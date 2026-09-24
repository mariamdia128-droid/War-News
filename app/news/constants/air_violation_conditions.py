"""Canonical air-violation condition IDs.

Condition 45 is intentionally excluded. It is a Red Alert internal fallback for
unclassified air activity and should not be treated as a routable air violation.
"""

AIR_VIOLATION_WARPLANE_CONDITION_ID = 35
AIR_VIOLATION_DRONE_CONDITION_ID = 36
AIR_VIOLATION_CONDITION_IDS = frozenset({
    AIR_VIOLATION_WARPLANE_CONDITION_ID,
    AIR_VIOLATION_DRONE_CONDITION_ID,
    38,
})
AIR_VIOLATION_CONDITION_ID_TUPLE = tuple(sorted(AIR_VIOLATION_CONDITION_IDS))
AIR_VIOLATION_SOUTH_CAZAS = frozenset({
    "Bint Jubail",
    "Hasbaya",
    "Jezzine",
    "Marjaayoun",
    "Nabatiye",
    "Saida",
    "Sour",
    "Zahrani",
})

