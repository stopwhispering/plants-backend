from enum import Enum
from pathlib import Path

from pydantic import BaseSettings, constr

from plants.extensions.config_values import parse_settings


class Environment(str, Enum):
    DEV = 'dev'
    PROD = 'prod'


class LogLevel(str, Enum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


class LogSettings(BaseSettings):
    log_level_console: LogLevel
    log_level_file: LogLevel
    log_file_path: Path
    ignore_missing_image_files: bool = False  # if True, missing image files will not result in Error; set in DEV only


class LocalConfig(BaseSettings):
    """Secrets and other environment-specific settings are specified in environment variables (or .env file)
    they are case-insensitive by default"""
    environment: Environment
    connection_string: constr(min_length=1, strip_whitespace=True)
    max_images_per_taxon: int = 20
    allow_cors: bool = False
    log_settings: LogSettings

    class Config:
        env_file = Path(__file__).resolve().parent.parent.joinpath('.env')
        env_file_encoding = 'utf-8'
        env_nested_delimiter = '__'


local_config = LocalConfig()
settings = parse_settings()
