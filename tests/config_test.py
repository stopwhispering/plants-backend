from pathlib import Path

from sqlalchemy.engine import URL
from pydantic import BaseSettings, constr


class TestConfig(BaseSettings):
    """Secrets and other environment-specific settings are specified in environment variables (or .env file)
    they are case-insensitive by default"""
    test_db_drivername: constr(min_length=1, strip_whitespace=True)
    test_db_username: constr(min_length=1, strip_whitespace=True)
    test_db_password: constr(min_length=1, strip_whitespace=True)
    test_db_host: constr(min_length=1, strip_whitespace=True)
    test_db_port: int

    class Config:
        env_file = Path(__file__).resolve().parent.parent.joinpath('.test.env')
        env_file_encoding = 'utf-8'


test_config = TestConfig()


def generate_db_url(database: str = 'postgres') -> URL:
    """
    postgres does not allow connection to <<no>> database (e.g. to create a new database),
    it will automtically try to connect to a database with same name as user if no database is specified
    therefore, we connect to the default maintenance database <<postgres>> if no database is specified
    """
    url = URL.create(drivername=test_config.test_db_drivername,
                     username=test_config.test_db_username,
                     password=test_config.test_db_password,
                     host=test_config.test_db_host,
                     port=test_config.test_db_port,
                     database=database,
                     )
    return url
