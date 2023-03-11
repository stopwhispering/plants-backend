from __future__ import annotations

from typing import Optional, TypeVar

T = TypeVar("T")


def cast_not_none(value: Optional[T]) -> T:
    assert value is not None  # noqa: S101
    return value
