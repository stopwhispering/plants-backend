import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()
engine = create_engine(os.getenv('CONNECTION_STRING'),
                       connect_args={'check_same_thread': False,
                                     # 'connect_timeout': 10
                                     })
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database_tables(engine_, session: Session = None):
    # import all orm tables. don't remove!
    import plants.models.event_models  # noqa
    import plants.models.history_model  # noqa
    import plants.models.image_models  # noqa
    import plants.models.plant_models  # noqa
    import plants.models.property_models  # noqa
    import plants.models.tag_models  # noqa
    import plants.models.taxon_models  # noqa
    import plants.models.trait_models  # noqa
    import plants.models.pollination_models  # noqa

    # create db tables if not existing
    Base.metadata.create_all(bind=engine_)

    # initially populate tables with default data
    from plants.models.event_models import insert_categories
    from plants.models.property_models import insert_property_categories
    insert_categories(SessionLocal() if not session else session)
    insert_property_categories(SessionLocal() if not session else session)


