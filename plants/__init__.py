from pathlib import Path

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
# print(dotenv_values())
env_path = Path(__file__).resolve().parent.parent.joinpath('.env')
load_dotenv(dotenv_path=env_path, override=True)

config = parse_config()
