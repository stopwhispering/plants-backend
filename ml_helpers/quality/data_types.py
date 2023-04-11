from __future__ import annotations

from typing import TYPE_CHECKING

from ml_helpers.numerical.util_numerical import is_number

if TYPE_CHECKING:
    import pandas as pd


def derive_dtype(ser: pd.Series) -> str:
    """Try to determine series dtype ignoring missing values."""
    series = ser[~ser.isna()]
    if series.apply(lambda x: str(x).isnumeric()).all():
        return "int"  # int is not nullable -> Exception
    if series.apply(lambda x: is_number(str(x))).all():
        return "float"  # float is nullable -> NaN
    # str is nullable -> 'nan'
    return str(series.convert_dtypes().dtype)
