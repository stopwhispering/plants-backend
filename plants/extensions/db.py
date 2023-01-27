from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine


def create_db_engine(connection_string: URL) -> Engine:
    """
    Engine is the lowest level object used by SQLAlchemy. It maintains a <<pool of connections>>.
    Connection is the thing that actually does the work of executing a SQL query. With the connection, you could
    run several different SQL statements and rollback if required.
    """
    if 'sqlite' in connection_string:
        return create_engine(connection_string, connect_args={'check_same_thread': False})
    else:
        return create_engine(connection_string)
