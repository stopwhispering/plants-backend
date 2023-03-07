from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

if TYPE_CHECKING:
    from sqlalchemy.engine import URL


def create_db_engine(connection_string: URL) -> AsyncEngine:
    """Engine is the lowest level object used by SQLAlchemy.

    It maintains a <<pool of connections>>. Connection is the thing that actually does
    the work of executing a SQL query. With the connection, you could run several
    different SQL statements and rollback if required.
    """
    if "sqlite" in connection_string:  # pragma: no cover
        return create_async_engine(
            connection_string, connect_args={"check_same_thread": False}
        )
    return create_async_engine(connection_string)
