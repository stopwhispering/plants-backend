from pathlib import Path

from pydantic import BaseSettings, constr
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from plants.extensions.orm import Base


class ConfigTest(BaseSettings):
    """Secrets and other environment-specific settings are specified in
    environment variables (or .env file) they are case-insensitive by
    default."""

    test_db_drivername: constr(min_length=1, strip_whitespace=True)
    test_db_username: constr(min_length=1, strip_whitespace=True)
    test_db_password: constr(min_length=1, strip_whitespace=True)
    test_db_host: constr(min_length=1, strip_whitespace=True)
    test_db_port: int

    class Config:
        env_file = Path(__file__).resolve().parent.parent.joinpath(".test.env")
        env_file_encoding = "utf-8"


test_config = ConfigTest()


def generate_db_url(database: str = "postgres") -> URL:
    """Postgres does not allow connection to <<no>> database (e.g. to create a
    new database), it will automtically try to connect to a database with same
    name as user if no database is specified therefore, we connect to the
    default maintenance database <<postgres>> if no database is specified."""
    url = URL.create(
        drivername=test_config.test_db_drivername,
        username=test_config.test_db_username,
        password=test_config.test_db_password,
        host=test_config.test_db_host,
        port=test_config.test_db_port,
        database=database,
    )
    return url


async def create_tables_if_required(engine: AsyncEngine):
    """Uses metadata's connection if no engine supplied."""
    # import all orm tables. don't remove!
    # this populates Base.metadata's list of tables
    import plants.modules.event.models  # noqa
    import plants.modules.image.models  # noqa
    import plants.modules.plant.models  # noqa
    import plants.modules.pollination.models  # noqa
    import plants.modules.taxon.models  # noqa
    import plants.shared.history_models  # noqa

    # create db tables if not existing
    async with engine.begin() as conn:
        conn: AsyncConnection
        await conn.run_sync(Base.metadata.create_all)
        # await conn.commit()
        # await conn.close()
