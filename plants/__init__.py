import toml
from dotenv import load_dotenv

from plants.extensions.config_values import parse_config

# override environment variables with values from .env file if
# available, otherwise keep system env. vars
# # example:
# import os
# os.getenv('CONNECTION_STRING')
#
# # show all .env env. vars:
# from dotenv import dotenv_values
# dotenv_values()
load_dotenv(dotenv_path='.env', override=True)

config = parse_config()
