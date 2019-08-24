import logging


def configure_root_logger():
    """configure the root logger; each module's default (__name__) logger will inherit these settings"""
    logger = logging.getLogger()  # no name returns the root loggre
    logger.setLevel(logging.DEBUG)  # global min. level

    # create file handler
    file_handler = logging.FileHandler('plants.log')
    file_handler.setLevel(logging.INFO)
    format_file = '%(asctime)s - %(threadName)-9s - %(funcName)s - %(name)s - %(levelname)s - %(message)s'
    file_handler.setFormatter(logging.Formatter(format_file))
    logger.addHandler(file_handler)

    # create console handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    format_stream = '%(name)s - %(levelname)s - %(message)s'
    stream_handler.setFormatter(logging.Formatter(format_stream))
    logger.addHandler(stream_handler)