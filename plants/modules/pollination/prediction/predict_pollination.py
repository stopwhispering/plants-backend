from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from sklearn import neighbors
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# noinspection PyProtectedMember
from sklearn.utils._testing import ignore_warnings

from plants.extensions.ml_models import pickle_pipeline
from plants.modules.pollination.enums import PredictionModel
from plants.modules.pollination.prediction.ml_common import assemble_data
from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
    Feature,
    FeatureContainer,
    Scale,
)

if TYPE_CHECKING:
    import pandas as pd
    from sklearn.base import BaseEstimator

logger = logging.getLogger(__name__)


def _create_pipeline(feature_container: FeatureContainer, model: BaseEstimator) -> Pipeline:
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

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("estimator", model),
        ]
    )


def _create_features() -> FeatureContainer:
    """Create a features container for a specific model to be trained."""
    features = [
        Feature(column="pollen_type", scale=Scale.NOMINAL_BIVALUE),
        Feature(column="species_seed_capsule", scale=Scale.NOMINAL),
        Feature(column="species_pollen_donor", scale=Scale.NOMINAL),
        Feature(column="genus_seed_capsule", scale=Scale.NOMINAL),
        Feature(column="genus_pollen_donor", scale=Scale.NOMINAL),
        Feature(column="same_genus", scale=Scale.BOOLEAN),
        # Feature(column='seed_capsule_length', scale=Scale.METRIC),
        # Feature(column='seed_capsule_width', scale=Scale.METRIC),
        # Feature(column='seed_length', scale=Scale.METRIC),
        # Feature(column='seed_width', scale=Scale.METRIC),
        # Feature(column='seed_count', scale=Scale.METRIC),
        # Feature(column='avg_ripening_time', scale=Scale.METRIC),
    ]
    # todo: pollination_timestamp (morning, evening, etc.) once enough data is available
    return FeatureContainer(features=features)


def _cv_classifier(x: pd.DataFrame, y: pd.Series, pipeline: Pipeline) -> tuple[str, float]:
    n_groups = 3  # test part will be 1/n
    n_splits = 3  # k-fold will score n times; must be <= n_groups
    rng = np.random.default_rng(42)
    kfold_groups = rng.integers(n_groups, size=len(x))
    group_kfold = GroupKFold(n_splits=n_splits)
    with ignore_warnings(category=(ConvergenceWarning, UserWarning)):
        scores = cross_val_score(pipeline, x, y, cv=group_kfold, groups=kfold_groups, scoring="f1")
    logger.info(f"Scores: {scores}")
    logger.info(f"Mean score: {np.mean(scores)}")
    return "mean_f1_score", round(float(np.mean(scores)), 2)


async def train_model_for_probability_of_seed_production() -> dict[str, str | float]:
    """Predict whether a pollination attempt is goint to reach SEED status."""
    feature_container = _create_features()
    df_all = await assemble_data(feature_container=feature_container, include_ongoing=False)
    # make sure we have only the labels we want (not each must be existent, though)
    if set(df_all.pollination_status.unique()) - {
        "seed_capsule",
        "germinated",
        "seed",
        "attempt",
    }:
        raise ValueError("Unexpected pollination status in dataset.")
    y: pd.Series = df_all["pollination_status"].apply(  # type: ignore[assignment]
        lambda s: 1 if s in {"seed_capsule", "seed", "germinated"} else 0
    )
    x: pd.DataFrame = df_all[feature_container.get_columns()]  # type: ignore[assignment]

    # train directly on full dataset with optimized hyperparams
    params_knn = {
        "algorithm": "ball_tree",
        "leaf_size": 20,
        "n_neighbors": 10,
        "p": 2,
        "weights": "distance",
    }
    model = neighbors.KNeighborsClassifier(**params_knn)
    pipeline = _create_pipeline(feature_container=feature_container, model=model)

    # show f1 cv score
    metric_name, metric_value = _cv_classifier(x, y, pipeline)

    # fit with full dataset
    pipeline.fit(x, y)
    pickle_pipeline(
        pipeline=pipeline,
        feature_container=feature_container,
        prediction_model=PredictionModel.POLLINATION_PROBABILITY,
    )
    return {
        "model": str(model),
        "metric_name": metric_name,
        "metric_value": metric_value,
    }
