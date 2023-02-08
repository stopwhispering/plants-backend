from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_db_engine(connection_string: URL) -> AsyncEngine:
    """
    Engine is the lowest level object used by SQLAlchemy. It maintains a <<pool of connections>>.
    Connection is the thing that actually does the work of executing a SQL query. With the connection, you could
    run several different SQL statements and rollback if required.
    """
    if 'sqlite' in connection_string:
        return create_async_engine(connection_string, connect_args={'check_same_thread': False})
    else:
        return create_async_engine(connection_string)
