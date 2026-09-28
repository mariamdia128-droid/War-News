"""Merge semantics of IncidentRepository._max_preserving_empty for NULL vs 0.

NULL means "not stated"; 0 is a stated zero. The merge keeps NULL only when both
sides are NULL, and otherwise takes the larger count.
"""

from __future__ import annotations

import pytest

from app.news.repositories.incident_repository import IncidentRepository

merge = IncidentRepository._max_preserving_empty


@pytest.mark.parametrize(
    ("current", "incoming", "expected"),
    [
        (None, None, None),
        (None, 0, 0),
        (0, None, 0),
        (None, 3, 3),
        (3, None, 3),
        (0, 2, 2),
        (4, 2, 4),
        (None, "3", None),
        (2, True, 2),
    ],
)
def test_max_preserving_empty(current, incoming, expected) -> None:
    assert merge(current, incoming) == expected
