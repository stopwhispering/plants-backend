from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    NONE = None


def configure_root_logger(
    log_severity_console: LogLevel,
    log_severity_file: LogLevel,
    log_file_path: Path = Path("./plants.log"),
    log_filter: logging.Filter | None = None,
) -> None:
    """Configure the root logger; each module's default (__name__) logger will inherit
    these settings."""
    logger = logging.getLogger()  # no name returns the root logger
    logger.setLevel(logging.DEBUG)  # global min. level
    # logging.basicConfig(level=logging.DEBUG)

    if log_severity_file != LogLevel.NONE:
        # create file handler
        file_handler = logging.FileHandler(log_file_path)
        format_fh = (
            "%(asctime)s - %(threadName)-9s - %(funcName)s - %(name)s - "
            "%(levelname)s - %(message)s"
        )
        formatter = logging.Formatter(format_fh)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_severity_file.value)
        # file_handler.setFormatter(logging.Formatter(format_file))
        logger.handlers = []
        logger.addHandler(file_handler)

    if log_severity_console != LogLevel.NONE:
        # create console handler
        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(log_severity_console.value)

        # format_stream = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        # format_stream = '%(levelname)s:%(message)s'
        # stream_handler.setFormatter(logging.Formatter(format_stream))
        logger.addHandler(stream_handler)

    # mute some module's loggers
    logging.getLogger("multipart.multipart").setLevel(
        logging.WARNING
    )  # starlette file requests
    logging.getLogger("PIL.TiffImagePlugin").setLevel(logging.WARNING)  # PIL Exif
    logging.getLogger("httpx._client").setLevel(
        logging.INFO
    )  # HTTPx (Requests replacement)
    logging.getLogger("asyncio").setLevel(logging.INFO)  # HTTPx (Requests replacement)

    if log_filter:
        logger.addFilter(log_filter)
