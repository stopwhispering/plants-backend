from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import FeatureContainer, Scale


def create_pipeline(feature_container: FeatureContainer, model: BaseEstimator):
    nominal_features = feature_container.get_columns(scale=Scale.NOMINAL)
    nominal_bivalue_features = feature_container.get_columns(scale=Scale.NOMINAL_BIVALUE)
    boolean_features = feature_container.get_columns(scale=Scale.BOOLEAN)
    ordinal_features = feature_container.get_columns(scale=Scale.ORDINAL)
    if ordinal_features:
        raise NotImplementedError("Ordinal features are not supported yet.")
    metric_features = feature_container.get_columns(scale=Scale.METRIC)

    one_hot_encoder = OneHotEncoder(handle_unknown="ignore")
    one_hot_encoder_bivalue = OneHotEncoder(handle_unknown="ignore", drop="if_binary")
    imputer_metric = SimpleImputer(strategy="mean")

    # create a pipeline to first impute, then scale our metric features
    metric_pipeline = Pipeline(
        steps=[
            ("imputer", imputer_metric),
            ("scaler", StandardScaler()),
        ]
    )

    # encode / scale / impute
    preprocessor = ColumnTransformer(
        sparse_threshold=0,  # generate np array, not sparse matrix
        remainder="drop",
        transformers=[
            ("impute_and_scale_metric", metric_pipeline, metric_features),
            ("one_hot", one_hot_encoder, nominal_features),
            ("one_hot_bivalue", one_hot_encoder_bivalue, nominal_bivalue_features),
            ("passthrough", "passthrough", boolean_features),
        ],
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("estimator", model),
        ]
    )

    return pipeline
