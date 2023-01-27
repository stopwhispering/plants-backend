from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from plants import local_config


Base = declarative_base()
if 'sqlite' in local_config.connection_string:
    # engine = create_engine(os.getenv('CONNECTION_STRING'), connect_args={'check_same_thread': False})
    engine = create_engine(local_config.connection_string, connect_args={'check_same_thread': False})
    # 'connect_timeout': 10
else:
    # engine = create_engine(os.getenv('CONNECTION_STRING'))
    engine = create_engine(local_config.connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database_tables(engine_, session: Session = None):
    # import all orm tables. don't remove!
    import plants.modules.event.models  # noqa
    import plants.shared.history_models  # noqa
    import plants.modules.image.models  # noqa
    import plants.modules.plant.models  # noqa
    import plants.modules.property.models  # noqa
    import plants.modules.taxon.models  # noqa
    import plants.modules.pollination.models  # noqa

    # create db tables if not existing
    Base.metadata.create_all(bind=engine_)

    # initially populate tables with default data
    # from plants.models.event_models import insert_categories
    from plants.modules.property.models import insert_property_categories
    # insert_categories(SessionLocal() if not session else session)
    insert_property_categories(SessionLocal() if not session else session)
