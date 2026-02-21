from __future__ import annotations
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ChatGroq expects the API key to be set in the environment variable GROQ_API_KEY.
if not os.getenv("GROQ_API_KEY"):
    BASE_DIR = Path(__file__).resolve().parent
    # env_path = BASE_DIR.parent / ".env"
    # env_path = BASE_DIR / "plants" / ".env"
    env_path = BASE_DIR / "plants" / "plants" / ".env"

    logger.error(f"CWD: {os.getcwd()}")  # /app

    logger.error(f"ENV exists at os.path: {os.path.exists('.env')}")

    logger.error(f"ENV exists at os.path: {os.path.exists('.env')}")  # False
    logger.error(f"ENV exists at env_path: {os.path.exists(env_path)}")  # False
    logger.error(f"ENV exists at base_dir: {os.path.exists(BASE_DIR / '.env')}")  # False
    logger.error(f"ENV exists at root: {os.path.exists('/.env')}")  # False
    logger.error(f"BASE_DIR: {BASE_DIR}")  # /app/plants

    files = os.listdir("/")
    logger.error(f"files at /: {files}")  # ['proc', 'dev', 'srv', 'opt', 'run', 'sbin', 'lib', 'root', 'home', 'boot', 'usr', 'lib64', 'etc', 'media', 'tmp', 'var', 'bin', 'mnt', 'sys', 'common', '.dockerenv', 'app', 'start-reload.sh', 'gunicorn_conf.py', 'start.sh']
    files = os.listdir("/app")
    logger.error(f"files at /app: {files}")  # ['prestart.sh', 'main.py', 'scripts', 'plants', 'ml_helpers', 'config.toml', 'alembic', 'alembic.ini', 'requirements.txt']
    files = os.listdir("/app/plants")
    logger.error(f"files at /app/plants: {files}")  # ['__init__.py', 'modules', 'extensions', 'constants.py', 'scripts', 'dependencies.py', 'shared', 'main.py', 'exceptions.py']
    # files = os.listdir("/app/plants/plants")  # No such file or directory: '/app/plants/plants'
    # logger.error(f"files at /app/plants/plants: {files}")

    load_dotenv(BASE_DIR.parent / ".env")
    if os.getenv("GROQ_API_KEY"):
        logger.info("Loaded GROQ_API_KEY from .env")
    else:
        logger.error(
            "GROQ_API_KEY not found in environment or .env."
        )

# Use a non-interactive backend, save the output to a file or a byte stream, rather than
# calling plt.show()
import matplotlib
matplotlib.use('Agg')

from plants.extensions.config_values import LocalConfig, parse_settings

local_config = LocalConfig()
settings = parse_settings()

# expose app to other modules, e.g. for app.state access
from plants.main import app  # , local_config, settings
