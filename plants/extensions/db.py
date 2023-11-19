from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_db_engine(connection_string: str) -> AsyncEngine:
    """Engine is the lowest level object used by SQLAlchemy.

    It maintains a <<pool of connections>>. Connection is the thing that actually does the work of
    executing a SQL query. With the connection, you could run several different SQL statements and
    rollback if required.
    """
    if "sqlite" in connection_string:  # pragma: no cover
        return create_async_engine(
            connection_string,
            connect_args={"check_same_thread": False},
            pool_size=15,
            max_overflow=3,
        )
    return create_async_engine(
        connection_string,
        # echo=True,
    )
