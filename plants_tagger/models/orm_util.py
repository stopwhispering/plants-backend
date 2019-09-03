from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from plants_tagger.config_local import connection_string

# using the <<base>> we can define any number of mapped classes
Base = declarative_base()
ScopedSession = None


def get_sql_session() -> ScopedSession:
    # all calls to ScopedSession() will create a thread-local session
    # noinspection PyCallingNonCallable
    return ScopedSession()


def init_sqlalchemy_engine():
    """connect to db via sqlalchemy and create engine"""
    if 'sqlite' in connection_string:
        engine = create_engine(connection_string, connect_args={'check_same_thread': False})
    else:
        engine = create_engine(connection_string)

    # create db tables if not existing
    Base.metadata.create_all(engine)
    # get a session factory
    session_factory = sessionmaker(bind=engine)

    # The ScopedSession object by default uses[threading.local()] as storage, so
    # that a single Session is maintained for all who
    # call upon the ScopedSession registry, but only within the
    # scope of a single thread.Callers who call upon the registry in a different
    # thread get a Session instance that is local to that other thread.
    global ScopedSession
    ScopedSession = scoped_session(session_factory)
