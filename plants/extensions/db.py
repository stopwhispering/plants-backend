from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from plants.config_local import connection_string

Base = declarative_base()
engine = create_engine(connection_string, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database_tables(engine_, session: Session = None):
    # import all orm tables. don't remove!
    import plants.models.event_models
    import plants.models.history_model
    import plants.models.image_models
    import plants.models.plant_models
    import plants.models.property_models
    import plants.models.tag_models
    import plants.models.taxon_models
    import plants.models.trait_models

    # create db tables if not existing
    Base.metadata.create_all(bind=engine_)

    # initially populate tables with default data
    from plants.models.event_models import insert_categories
    from plants.models.property_models import insert_property_categories
    insert_categories(SessionLocal() if not session else session)
    insert_property_categories(SessionLocal() if not session else session)
