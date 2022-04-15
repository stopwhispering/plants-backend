import logging
from pathlib import Path


def configure_root_logger(log_severity_console,
                          log_severity_file,
                          log_file_path: Path = Path('./plants.log'),
                          log_filter: logging.Filter = None):
    """configure the root logger; each module's default (__name__) logger will inherit these settings"""
    logger = logging.getLogger()  # no name returns the root logger
    logger.setLevel(logging.DEBUG)  # global min. level
    # logging.basicConfig(level=logging.DEBUG)

    # create file handler
    file_handler = logging.FileHandler(log_file_path)
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(threadName)-9s - %(funcName)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_severity_file)
    # format_file = '%(asctime)s - %(threadName)-9s - %(funcName)s - %(name)s - %(levelname)s - %(message)s'
    # file_handler.setFormatter(logging.Formatter(format_file))
    logger.handlers = []
    logger.addHandler(file_handler)

    # create console handler
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_severity_console)

    # format_stream = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    # format_stream = '%(levelname)s:%(message)s'
    # stream_handler.setFormatter(logging.Formatter(format_stream))
    logger.addHandler(stream_handler)

    # mute some module's loggers
    logging.getLogger('multipart.multipart').setLevel(logging.WARNING)  # starlette file requests
    logging.getLogger('PIL.TiffImagePlugin').setLevel(logging.WARNING)  # PIL Exif

    if log_filter:
        logger.addFilter(log_filter)
