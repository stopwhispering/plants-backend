from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def cast_not_none(value: T | None) -> T:
    assert value is not None  # noqa: S101
    return value
