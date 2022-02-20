from os import getenv
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Tuple

import toml

from plants.util.filename_utils import create_if_not_exists


@dataclass
class Configuration:
    size_preview_image: Tuple[int, int]  # e.g.[300, 300]
    size_thumbnail_image_taxon: Tuple[int, int]  # e.g.[220, 1000]
    size_thumbnail_image: Tuple[int, int]  # e.g.[350, 350]
    resizing_size: Tuple[int, int]  # e.g.[3440, 1440]
    jpg_quality: int  # e.g. 82

    filter_hidden_plants: bool

    log_severity_console: str  # e.g. 'DEBUG', will be mapped to int
    log_severity_file: int
    log_ignore_missing_image_files: bool
    allow_cors: bool

    max_images_per_taxon: int  # e.g.10
    n_plants: int  # e.g. 50

    path_photos_base: Path
    subdirectory_photos: PurePath  # 'localService'
    path_deleted_photos: Path  # 'C:\\common\\plants\\photos\\deleted'

    path_original_photos: Path
    path_original_photos_uploaded: Path
    path_generated_thumbnails: Path
    path_generated_thumbnails_taxon: Path

    rel_path_photos_generated_taxon: PurePath
    rel_path_photos_original: PurePath
    rel_path_photos_generated: PurePath


def parse_config() -> Configuration:
    """Configuration is specified in environment variables (or .env file) and in config.toml
    - environment variables contain paswords/secrets and whether we're  on 'dev' or 'prod'
        here, we only use the latter information
    - config.toml contains global configuration and environment-specific configuration values
    """
    environment = getenv('ENVIRONMENT').lower()

    config_global = toml.load("config.toml")
    config_env = config_global['environments'][environment]

    path_photos_base = Path(config_env['path_photos'])
    path_original_photos = path_photos_base.joinpath('original')
    path_original_photos_uploaded = path_original_photos.joinpath('uploaded')
    path_generated_thumbnails = path_photos_base.joinpath('generated')
    path_generated_thumbnails_taxon = path_photos_base.joinpath('generated_taxon')

    # subdirectory_photos = PurePath(config_env['subdirectory_photos'])
    subdirectory_photos = PurePath(path_photos_base.name)
    rel_path_photos_generated_taxon = subdirectory_photos.joinpath("generated_taxon")
    rel_path_photos_original = subdirectory_photos.joinpath("original")
    rel_path_photos_generated = subdirectory_photos.joinpath("generated")

    config = Configuration(
        size_preview_image=config_global['images']['size_preview_image'],
        size_thumbnail_image_taxon=config_global['images']['size_thumbnail_image_taxon'],
        size_thumbnail_image=config_global['images']['size_thumbnail_image'],
        resizing_size=config_global['images']['resizing_size'],
        jpg_quality=config_global['images']['jpg_quality'],
        filter_hidden_plants=config_global['plants']['filter_hidden'],

        log_severity_console=config_env['log_severity_console'].upper(),
        log_severity_file=config_env['log_severity_file'].upper(),
        log_ignore_missing_image_files=config_env['log_ignore_missing_image_files'],
        allow_cors=config_env['allow_cors'],
        max_images_per_taxon=config_env['max_images_per_taxon'],
        n_plants=config_env['n_plants'],

        path_photos_base=path_photos_base,
        subdirectory_photos=subdirectory_photos,
        path_deleted_photos=Path(config_env['path_deleted_photos']),
        path_original_photos=path_original_photos,
        path_original_photos_uploaded=path_original_photos_uploaded,
        path_generated_thumbnails=path_generated_thumbnails,
        path_generated_thumbnails_taxon=path_generated_thumbnails_taxon,
        rel_path_photos_generated_taxon=rel_path_photos_generated_taxon,
        rel_path_photos_original=rel_path_photos_original,
        rel_path_photos_generated=rel_path_photos_generated,
        )

    # create folders not yet existing
    create_if_not_exists(folders=[config.path_deleted_photos,
                                  config.path_generated_thumbnails,
                                  config.path_generated_thumbnails_taxon,
                                  config.path_original_photos_uploaded], parents=True)

    return config