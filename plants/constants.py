from __future__ import annotations

from typing import Final

RESIZE_SUFFIX: Final[str] = "_autoresized"
REGEX_DATE: Final[
    str
] = r"^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$"  # string yyyy-mm-dd
FILENAME_PICKLED_POLLINATION_ESTIMATOR = "pollination_estimator.pkl"
