import pandas as pd

from ml_helpers.quality.data_types import derive_dtype


def _get_min(ser_report: pd.Series, ser_data: pd.Series):
    """get min value for supplied data values ignoring missing values;
    this requires filling nan before"""
    try:
        imp = ser_report['frequent_value']
        if imp is None:
            return None
        dtype = ser_report['derived_dtype']
        return ser_data.fillna(imp).astype(dtype).min()

    except TypeError:
        return ''


def _get_max(ser_report: pd.Series, ser_data: pd.Series):
    """get max value for supplied data values ignoring missing values;
    this requires filling nan before"""
    try:
        imp = ser_report['frequent_value']
        if imp is None:
            return None
        dtype = ser_report['derived_dtype']
        return ser_data.fillna(imp).astype(dtype).max()
    except TypeError:
        return ''


def _get_col_evaluation(df: pd.DataFrame, only_with_missing=False) -> pd.DataFrame:
    report = df.isnull().sum().to_frame('missing_values')  # noqa
    if only_with_missing:
        report = report.loc[report['missing_values'] != 0]
    report['%'] = (report['missing_values'] / df.shape[0]).round(2)
    report['dtype'] = report.index.map(lambda c: df[c].dtype)
    report['derived_dtype'] = report.index.map(lambda c: derive_dtype(df[c]))
    report['nunique'] = report.index.map(lambda c: df[c].nunique())
    # avoid errors due to all-nan columns
    all_nan_cols = report.loc[report['nunique'] == 0].index
    report['frequent_value'] = report.index.map(lambda c: df[c].mode(dropna=True).iloc[0] if c not in all_nan_cols else None)

    if not report.empty:
        report['min'] = report.apply(lambda row: _get_min(row, df[row.name]), axis=1)
        report['max'] = report.apply(lambda row: _get_max(row, df[row.name]), axis=1)

    return report


def print_col_evaluation(df: pd.DataFrame) -> pd.DataFrame:
    report = _get_col_evaluation(df=df, only_with_missing=False)
    # print all columns
    default = pd.get_option('display.max_columns')
    pd.set_option('display.max_columns', None)
    report.sort_values(by='missing_values', ascending=False, inplace=True)
    print(report.sort_values(by='missing_values', ascending=False))
    pd.set_option('display.max_columns', default)
    return report


def print_nan_evaluation(df: pd.DataFrame) -> pd.DataFrame | None:
    report = _get_col_evaluation(df=df, only_with_missing=True)

    if not report.empty:
        # print all columns
        default = pd.get_option('display.max_columns')
        pd.set_option('display.max_columns', None)
        report.sort_values(by='missing_values', ascending=False, inplace=True)
        print(report)
        pd.set_option('display.max_columns', default)
        return report

    else:
        print('No missing values found.')
