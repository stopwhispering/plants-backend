from enum import Enum
from pathlib import Path

from pydantic import BaseSettings
from dotenv import load_dotenv


class Environment(str, Enum):
    DEV = 'dev'
    PROD = 'prod'


class SecretsConfig(BaseSettings):
    """Secrets are specified in environment variables (or .env file)
    they are case-insensitive by default"""
    environment: Environment
    connection_string: str

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


# override environment variables with values from .env file if
# available, otherwise keep system env. vars
# # example:
# import os
# os.getenv('CONNECTION_STRING')
#
# # show all .env env. vars:
# from dotenv import dotenv_values
# print(dotenv_values())
secrets_config = SecretsConfig()


from plants.extensions.config_values import parse_config  # noqa
env_path = Path(__file__).resolve().parent.parent.joinpath('.env')
load_dotenv(dotenv_path=env_path, override=True)

config = parse_config()
