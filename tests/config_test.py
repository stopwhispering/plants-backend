from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from pydantic import Field  # noqa: TCH002
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from plants.extensions.orm import Base

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine


class ConfigTest(BaseSettings):
    """Secrets and other environment-specific settings are specified in environment variables (or.

    .env file) they are case-insensitive by default.
    """

    # test_db_drivername: constr(min_length=1, strip_whitespace=True)  # type: ignore[valid-type]
    test_db_drivername: Annotated[str, Field(min_length=1, strip_whitespace=True)]
    # test_db_username: constr(min_length=1, strip_whitespace=True)  # type: ignore[valid-type]
    test_db_username: Annotated[str, Field(min_length=1, strip_whitespace=True)]
    # test_db_password: constr(min_length=1, strip_whitespace=True)  # type: ignore[valid-type]
    test_db_password: Annotated[str, Field(min_length=1, strip_whitespace=True)]
    # test_db_host: constr(min_length=1, strip_whitespace=True)  # type: ignore[valid-type]
    test_db_host: Annotated[str, Field(min_length=1, strip_whitespace=True)]

    test_db_port: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    # class Config:
    #     env_file = Path(__file__).resolve().parent.parent.joinpath(".test.env")
    #     env_file_encoding = "utf-8"


test_config = ConfigTest(
    _env_file=Path(__file__).resolve().parent.parent.joinpath(".test.env"),
    _env_file_encoding="utf-8",
)


def generate_db_url(database: str = "postgres") -> URL:
    """Postgres does not allow connection to <<no>> database (e.g. to create a new database), it
    will automtically try to connect to a database with same name as user if no database is
    specified therefore, we connect to the default maintenance database <<postgres>> if no database
    is specified."""
    return URL.create(
        drivername=test_config.test_db_drivername,
        username=test_config.test_db_username,
        password=test_config.test_db_password,
        host=test_config.test_db_host,
        port=test_config.test_db_port,
        database=database,
    )


async def create_tables_if_required(engine: AsyncEngine) -> None:
    """Uses metadata's connection if no engine supplied."""
    # import all orm tables. don't remove!
    # this populates Base.metadata's list of tables
    import plants.modules.event.models  # pylint: disable=C0415
    import plants.modules.image.models  # pylint: disable=C0415
    import plants.modules.plant.models  # pylint: disable=C0415
    import plants.modules.pollination.models  # pylint: disable=C0415
    import plants.modules.taxon.models  # pylint: disable=C0415
    import plants.shared.history_models  # noqa: F401  # pylint: disable=C0415

    # create db tables if not existing
    conn: AsyncConnection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # await conn.commit()
        # await conn.close()
