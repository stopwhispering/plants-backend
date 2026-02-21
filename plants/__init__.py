from __future__ import annotations


# Use a non-interactive backend, save the output to a file or a byte stream, rather than
# calling plt.show()
import matplotlib
matplotlib.use('Agg')

from plants.extensions.config_values import LocalConfig, parse_settings

local_config = LocalConfig()
settings = parse_settings()

# expose app to other modules, e.g. for app.state access
from plants.main import app  # , local_config, settings
