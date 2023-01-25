from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Tuple

import toml

from ml_helpers.preprocessing.features import DBType
from plants import secrets_config
from plants.util.filename_utils import create_if_not_exists


@dataclass
class Configuration:
    size_thumbnail_image_taxon: Tuple[int, int]  # e.g.[220, 220]
    sizes: Tuple[Tuple[int, int], ...]  # required lower-resolution sizes for images
    resizing_size: Tuple[int, int]  # e.g.[3440, 1440]
    jpg_quality: int  # e.g. 82

    filter_hidden_plants: bool

    taxon_search_max_results: int

    log_severity_console: str  # e.g. 'DEBUG', will be mapped to int
    log_severity_file: int
    log_file_path: Path
    # if True, missing image files will not be logged and a default image will be used instead
    ignore_missing_image_files: bool
    allow_cors: bool

    max_images_per_taxon: int  # e.g.10
    n_plants: int  # e.g. 50

    path_photos_base: Path
    subdirectory_photos: PurePath  # 'localService'
    path_deleted_photos: Path  # 'C:\\common\\plants\\photos\\deleted'

    path_original_photos_uploaded: Path
    path_generated_thumbnails: Path
    path_generated_thumbnails_taxon: Path

    rel_path_photos_generated_taxon: PurePath
    rel_path_photos_original: PurePath
    rel_path_photos_generated: PurePath

    path_pickled_ml_models: Path

    db_type: DBType  # 'postgres' or 'sqlite' or 'unknown'


def parse_config() -> Configuration:
    """Configuration is specified in environment variables (or .env file) and in config.toml
    - environment variables contain paswords/secrets and whether we're  on 'dev' or 'prod'
        here, we only use the latter information
    - config.toml contains global configuration and environment-specific configuration values
    """
    config_toml_path = Path(__file__).resolve().parent.parent.parent.joinpath('config.toml')
    config_global = toml.load(config_toml_path)
    config_env = config_global['environments'][secrets_config.environment]

    path_photos_base = Path(config_env['path_photos'])
    path_original_photos = path_photos_base.joinpath('original')
    path_original_photos_uploaded = path_original_photos.joinpath('uploaded')
    path_generated_thumbnails = path_photos_base.joinpath('generated')
    path_generated_thumbnails_taxon = path_photos_base.joinpath('generated_taxon')

    subdirectory_photos = PurePath(path_photos_base.name)
    rel_path_photos_generated_taxon = subdirectory_photos.joinpath("generated_taxon")
    rel_path_photos_original = subdirectory_photos.joinpath("original")
    rel_path_photos_generated = subdirectory_photos.joinpath("generated")

    if 'sqlite' in secrets_config.connection_string:
        db_type = DBType.SQLITE
    elif 'postgres' in secrets_config.connection_string:
        db_type = DBType.POSTGRES
    else:
        db_type = DBType.UNKNOWN

    config = Configuration(
        size_thumbnail_image_taxon=config_global['images']['size_thumbnail_image_taxon'],
        resizing_size=tuple(config_global['images']['resizing_size']),
        sizes=tuple(tuple(s) for s in config_global['images']['sizes']),
        jpg_quality=config_global['images']['jpg_quality'],
        filter_hidden_plants=config_global['plants']['filter_hidden'],

        taxon_search_max_results=config_global['plants']['taxon_search_max_results'],

        log_severity_console=config_env['log_severity_console'].upper(),
        log_severity_file=config_env['log_severity_file'].upper(),
        log_file_path=Path(config_env['log_file_path']),
        ignore_missing_image_files=config_env['ignore_missing_image_files'],
        allow_cors=config_env['allow_cors'],
        max_images_per_taxon=config_env['max_images_per_taxon'],
        n_plants=config_env['n_plants'],

        path_photos_base=path_photos_base,
        subdirectory_photos=subdirectory_photos,
        path_deleted_photos=Path(config_env['path_deleted_photos']),
        # path_original_photos=path_original_photos,
        path_original_photos_uploaded=path_original_photos_uploaded,
        path_generated_thumbnails=path_generated_thumbnails,
        path_generated_thumbnails_taxon=path_generated_thumbnails_taxon,
        rel_path_photos_generated_taxon=rel_path_photos_generated_taxon,
        rel_path_photos_original=rel_path_photos_original,
        rel_path_photos_generated=rel_path_photos_generated,
        path_pickled_ml_models=Path(config_env['path_pickled_ml_models']),
        db_type=db_type,
        )

    # create folders not yet existing
    create_if_not_exists(folders=[config.path_deleted_photos,
                                  config.path_generated_thumbnails,
                                  config.path_generated_thumbnails_taxon,
                                  config.path_original_photos_uploaded,
                                  config.path_pickled_ml_models], parents=True)

    return config
