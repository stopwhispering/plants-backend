import logging

########################################################################################################################
LOG_SEVERITY_CONSOLE = logging.DEBUG
LOG_SEVERITY_FILE = logging.INFO
LOG_IS_DEV = True  # skip some log entries due to missing image files

########################################################################################################################
# allow cors on development system if no reverse proxy available
ALLOW_CORS = True

########################################################################################################################
connection_string = 'sqlite:///C:\\temp\\database.db'

########################################################################################################################
# path configuration
PATH_BASE = r"C:\Workspaces\VS Code Projects\plants_frontend\webapp"

# may not be a subfolder of PATH_PHOTOS_BASE
PATH_DELETED_PHOTOS = r'C:\common\plants\photos\deleted'

SUBDIRECTORY_PHOTOS = 'localService'
