from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from typing import List, Callable
import logging

from plants_tagger.config_local import connection_string


Base = declarative_base()
ScopedSession = None
logger = logging.getLogger(__name__)


def get_sql_session() -> ScopedSession:
    # all calls to ScopedSession() will create a thread-local session
    # noinspection PyCallingNonCallable
    return ScopedSession()


# noinspection PyUnresolvedReferences
def init_sqlalchemy_engine(followup_funcs: List[Callable] = None):
    """connect to extensions via sqlalchemy and create engine
    optionally supply list of functions w/o further arguments for table initialization, e.g. inserting
    default values into a extensions table"""

    logging.getLogger(__name__).info('Initializing SQLAlchemy Engine')
    if 'sqlite' in connection_string:
        engine = create_engine(connection_string, connect_args={'check_same_thread': False})
    else:
        engine = create_engine(connection_string)

    # import all orm tables. don't remove!
    import plants_tagger.models.event_models
    import plants_tagger.models.image_models
    import plants_tagger.models.plant_models
    # import plants_tagger.models.property_models
    import plants_tagger.models.taxon_models
    import plants_tagger.models.trait_models
    # import plants_tagger.models.taxon2
    import plants_tagger.models.history_model
    import plants_tagger.models.tag_models
    import plants_tagger.models.property_models

    # create extensions tables if not existing
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

    # execute initialization functions
    if followup_funcs:
        for func in followup_funcs:
            func()
