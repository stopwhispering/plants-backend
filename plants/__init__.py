from __future__ import annotations
import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ChatGroq expects the API key to be set in the environment variable GROQ_API_KEY.
if not os.getenv("GROQ_API_KEY"):
    load_dotenv()
    if os.getenv("GROQ_API_KEY"):
        logger.info("Loaded GROQ_API_KEY from .env")
    else:
        logger.warning(
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
