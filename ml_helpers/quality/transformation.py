from typing import List, Tuple

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.compose import ColumnTransformer
from sklearn.impute import KNNImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler


def _get_feature_names_from_transformer(name, transformer, columns) -> List[str]:
    """from a supplied transformer (usually step in a ColumnTransformer), try to return
    meaningful output column name(s)"""
    if name == "drop" or transformer == "drop" or not columns:
        return []

    elif name == "passthrough":
        return columns

    elif (
        isinstance(transformer, RobustScaler)
        or isinstance(transformer, MinMaxScaler)
        or isinstance(transformer, StandardScaler)
    ):
        return columns

    elif type(transformer) is Pipeline:
        # call same function recursively for the first step of the pipeline
        # todo not really working; make this better
        # if last step is a scaler, use the first step, otherwise the last (e.g. onehotencoder)
        if str(transformer.steps[-1][1]).find("Scaler") >= 0:
            relevant_pipeline_trf = transformer.steps[0][1]
        else:
            relevant_pipeline_trf = transformer.steps[-1][1]
        return _get_feature_names_from_transformer(name, relevant_pipeline_trf, columns)

        # names = list(last_pipeline_trf.get_feature_names_out())
        # # replace auto-named (e.g. 'x0', 'x1', etc.) columns
        # names = [name + '_' + n if re.match(r'^x\d$', n) else n for n in names]
        # return names

    elif type(transformer) is KNNImputer:
        # KNNImputer has no get_feature_names fn, but doesn't alter columns count anyway)
        return [n for n in columns]

    # elif isinstance(transformer, _OneToOneFeatureMixin):
    #     # _OneToOneFeatureMixin provides get_feature_names_out() for one-in-one-out-transformers
    #     return list(transformer.get_feature_names_out())

    else:
        try:
            names = list(
                transformer.get_feature_names_out()
            )  # list() does not result in cx if is already list
            return names
        except AttributeError as e:
            pass

        try:
            names = list(transformer.get_feature_names())
            return names
        except AttributeError as e:
            raise e


def get_transformed_df_from_column_transformer(
    column_transformer: ColumnTransformer, x: pd.DataFrame
) -> Tuple[List[str], pd.DataFrame]:
    """from a fitted column transformer, extract the new column names, i.e. including
    one-hot-encoded columns etc.

    create a DataFrame from transformed data with the found column names
    todo: incomplete and buggy; only ad-hoc-usage
    Example Usage:
        feature_names, df_transformed = get_transformed_df_from_column_transformer(column_transformer, x)
    """
    feature_names = []
    transformed_arr = []

    # note that column_transformer.transformers contains the <<unfitted>> transformers
    if not hasattr(column_transformer, "transformers_"):
        raise ValueError("column_transformer must be fitted first")
    for name, transformer, columns in column_transformer.transformers_:
        names = _get_feature_names_from_transformer(name, transformer, columns)
        if not names:
            continue
        feature_names.extend(names)

        if transformer == "passthrough":
            transformed_arr.append(x[columns].values)
        # elif transformer == 'drop':
        #     continue
        else:
            arr_current_transformer = transformer.transform(x[columns])

            # uncompress sparse matrix
            if type(arr_current_transformer) is csr_matrix:
                arr_current_transformer = arr_current_transformer.todense()

            if not arr_current_transformer.shape[1] == len(names):
                raise ValueError(
                    r"Number of transformed columns doesn't match derived new names."
                )

            transformed_arr.append(arr_current_transformer)

    values = np.concatenate(transformed_arr, axis=1)
    df_transformed = pd.DataFrame(values, columns=feature_names)

    # assert our self-assembled values from all steps' transformations are equal to the whole column
    # transformer's transformation
    df_transformed_at_once = pd.DataFrame(
        column_transformer.transform(x), columns=feature_names
    )
    if not (df_transformed_at_once == df_transformed).all().all():
        raise ValueError("Some error happened. Should be equal for all columns.")

    return feature_names, df_transformed
