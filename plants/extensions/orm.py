from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# Base is the the base class for ORM models
# All tables implicitly declared by subclasses of the base will share it's MetaData
# object.
# Metadata is an object that knows about database objects, primarily tables; it's a
# list of known tables is populated
# by importing them.
Base = declarative_base()


class SessionFactory:
    # Sessions are used for the Object Relationship Management (ORM) aspect of
    # SQLAlchemy  They use connections and
    # transactions under the hood to run their automatically-generated SQL statements.
    # It keeps track of new,
    # removed and changed ORM model instances while they are in use.
    session_factory: sessionmaker = None

    @classmethod
    def create_sessionmaker(cls, engine: AsyncEngine) -> None:
        """Create a sessionmaker for a given db engine."""
        cls.session_factory = sessionmaker(  # noqa
            engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    @classmethod
    def create_session(cls):
        return cls.session_factory()

    @classmethod
    def get_session_factory(cls):
        if cls.session_factory is None:
            raise ValueError("Session factory not set")
        return cls.session_factory


async def init_orm(engine: AsyncEngine):
    SessionFactory.create_sessionmaker(engine=engine)
