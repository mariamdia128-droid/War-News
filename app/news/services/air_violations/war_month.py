from datetime import date


def war_month(value: date) -> int:
    """Return the April-based month number used by the war dataset."""
    return ((value.month - 4) % 12) + 1
