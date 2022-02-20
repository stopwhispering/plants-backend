from os import getenv
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import toml


@dataclass
class Configuration:
    size_preview_image: Tuple[int, int]  # e.g.[300, 300]
    size_tumbnail_image_taxon: Tuple[int, int]  # e.g.[220, 1000]
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

    path_base: Path  # "C:\\Workspaces\\VS Code Projects\\plants_frontend\\webapp"
    subdirectory_photos: Path  # 'localService'
    path_deleted_photos: Path  # 'C:\\common\\plants\\photos\\deleted'


def parse_config() -> Configuration:
    """Configuration is specified in environment variables (or .env file) and in config.toml
    - environment variables contain paswords/secrets and whether we're  on 'dev' or 'prod'
        here, we only use the latter information
    - config.toml contains global configuration and environment-specific configuration values
    """
    environment = getenv('environment').lower()

    config_global = toml.load("config.toml")
    config_env = config_global['environments'][environment]

    config = Configuration(
        size_preview_image=config_global['images']['size_preview_image'],
        size_tumbnail_image_taxon=config_global['images']['size_tumbnail_image_taxon'],
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
        path_base=config_env['path_base'],
        subdirectory_photos=config_env['subdirectory_photos'],
        path_deleted_photos=config_env['path_deleted_photos'])

    return config

