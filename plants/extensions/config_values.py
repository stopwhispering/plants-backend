from enum import Enum
from pathlib import Path, PurePath
from typing import Tuple

import toml
from pydantic import BaseModel, BaseSettings, constr

from plants.util.filename_utils import create_if_not_exists


class ImageSettings(BaseModel):
    size_thumbnail_image_taxon: Tuple[int, int]  # e.g.[220, 220]
    sizes: Tuple[Tuple[int, int], ...]  # required lower-resolution sizes for images
    resizing_size: Tuple[int, int]  # e.g.[3440, 1440]
    jpg_quality: int  # e.g. 82


class PlantSettings(BaseModel):
    filter_hidden: bool
    taxon_search_max_results: int


class FrontendRestrictions(BaseModel):
    length_shortened_plant_name_for_tag: int


class FrontendSettings(BaseModel):
    restrictions: FrontendRestrictions


class PathSettings(BaseModel):
    path_photos: Path
    path_deleted_photos: Path
    path_pickled_ml_models: Path
    # db_type: DBType  # 'postgres' or 'sqlite' or 'unknown'

    # todo cleanup properties: most are used only once or twice

    @property
    def subdirectory_photos(self) -> PurePath:
        # todo remove
        return PurePath(self.path_photos.name)

    @property
    def path_original_photos_uploaded(self) -> Path:
        return self.path_photos.joinpath('original/uploaded')

    @property
    def path_generated_thumbnails(self) -> Path:
        return self.path_photos.joinpath('generated')

    @property
    def path_generated_thumbnails_taxon(self) -> Path:
        return self.path_photos.joinpath('generated_taxon')

    @property
    def rel_path_photos_generated_taxon(self) -> PurePath:
        # todo remove?
        return self.subdirectory_photos.joinpath("generated_taxon")

    @property
    def rel_path_photos_original(self) -> PurePath:
        # todo remove?
        return self.subdirectory_photos.joinpath("original")

    @property
    def rel_path_photos_generated(self) -> PurePath:
        # todo remove?
        return self.subdirectory_photos.joinpath("generated")


class Settings(BaseModel):
    images: ImageSettings
    plants: PlantSettings
    frontend: FrontendSettings
    paths: PathSettings


def parse_settings() -> Settings:
    config_toml_path = Path(__file__).resolve().parent.parent.parent.joinpath('config.toml')
    settings = Settings.parse_obj(toml.load(config_toml_path))

    create_if_not_exists(folders=[settings.paths.path_deleted_photos,
                                  settings.paths.path_generated_thumbnails,
                                  settings.paths.path_generated_thumbnails_taxon,
                                  settings.paths.path_original_photos_uploaded,
                                  settings.paths.path_pickled_ml_models], parents=True)

    return settings


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
        env_file = Path(__file__).resolve().parent.parent.parent.joinpath('.env')
        env_file_encoding = 'utf-8'
        env_nested_delimiter = '__'
