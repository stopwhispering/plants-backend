from __future__ import annotations


def is_number(s: str) -> bool:
    """Str.isnumeric() returns False for floats, so we make up our own number
    checker."""
    try:
        float(s)
    except ValueError:
        return False
    return True
