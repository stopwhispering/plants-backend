import pandas as pd

from ml_helpers.numerical.util_numerical import is_number


def derive_dtype(ser: pd.Series):
    """Try to determine series dtype ignoring missing values."""
    series = ser[~ser.isnull()]
    if series.apply(lambda x: str(x).isnumeric()).all():
        return "int"  # int is not nullable -> Exception
    elif series.apply(lambda x: is_number(str(x))).all():
        return "float"  # float is nullable -> NaN
    else:
        # str is nullable -> 'nan'
        return str(series.convert_dtypes().dtype)
