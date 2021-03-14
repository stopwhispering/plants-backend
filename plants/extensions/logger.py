from plants.util.logger_utils import configure_root_logger
from plants.config_local import LOG_SEVERITY_CONSOLE, LOG_SEVERITY_FILE


configure_root_logger(LOG_SEVERITY_CONSOLE, LOG_SEVERITY_FILE)
