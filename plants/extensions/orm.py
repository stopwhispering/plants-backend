from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# Base is the the base class for ORM models
# All tables implicitly declared by subclasses of the base will share it's MetaData object.
# Metadata is an object that knows about database objects, primarily tables; it's a list of known tables is populated
# by importing them.
Base = declarative_base()


class SessionFactory:
    # Sessions are used for the Object Relationship Management (ORM) aspect of SQLAlchemy  They use connections and
    # transactions under the hood to run their automatically-generated SQL statements. It keeps track of new,
    # removed and changed ORM model instances while they are in use.
    session_factory: sessionmaker = None

    @classmethod
    def create_sessionmaker(cls, engine: AsyncEngine) -> None:
        """Create a sessionmaker for a given db engine."""
        cls.session_factory = sessionmaker(engine,  # noqa
                                           autocommit=False,
                                           autoflush=False,
                                           expire_on_commit=False,
                                           class_=AsyncSession)

    @classmethod
    def create_session(cls):
        return cls.session_factory()

    @classmethod
    def get_session_factory(cls):
        if cls.session_factory is None:
            raise Exception("Session factory not set")
        return cls.session_factory


async def init_orm(engine: AsyncEngine):
    SessionFactory.create_sessionmaker(engine=engine)

    await create_tables_if_required(engine)

    # initially populate tables with default data
    from plants.modules.property.populate_table import insert_property_categories
    await insert_property_categories(SessionFactory.create_session())


async def create_tables_if_required(engine: AsyncEngine):
    """uses metadata's connection if no engine supplied"""
    # import all orm tables. don't remove!
    # this populates Base.metadata's list of tables
    import plants.modules.event.models  # noqa
    import plants.shared.history_models  # noqa
    import plants.modules.image.models  # noqa
    import plants.modules.plant.models  # noqa
    import plants.modules.property.models  # noqa
    import plants.modules.taxon.models  # noqa
    import plants.modules.pollination.models  # noqa

    # create db tables if not existing
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
