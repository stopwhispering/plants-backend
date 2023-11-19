from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# noinspection PyProtectedMember
from sklearn.utils._testing import ignore_warnings

from plants.modules.pollination.enums import PredictionModel
from plants.modules.pollination.prediction.ml_common import (
    pickle_pipeline,
)
from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
    Feature,
    FeatureContainer,
    Scale,
)
from plants.modules.pollination.prediction.pollination_data import assemble_pollination_data

if TYPE_CHECKING:
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


def make_preprocessor(df: pd.DataFrame) -> ColumnTransformer:
    categorical_features = [
        # "location",
        "genus_seed_capsule",
        "species_seed_capsule",
        "genus_pollen_donor",
        "species_pollen_donor",
        "pollen_type",
    ]

    boolean_features = [
        "hybrid_seed_capsule",
        "hybridgenus_seed_capsule",
        "hybrid_pollen_donor",
        "hybridgenus_pollen_donor",
        "same_genus",
        "same_species",
    ]

    dropped = [c for c in df.columns if c not in categorical_features + boolean_features]
    logger.info(f"Columns not used for prediction:\n{dropped}")

    missing = [c for c in categorical_features + boolean_features if c not in df.columns]
    if missing:
        raise ValueError(f"Missing:\n{missing}")

    one_hot_encoder = OneHotEncoder(
        handle_unknown="ignore",  # all zeros for unknown
        sparse_output=False,
    )

    return ColumnTransformer(
        transformers=[
            ("cat", one_hot_encoder, categorical_features),
            ("bool", "passthrough", boolean_features),
        ],
        remainder="drop",
    )


def create_ensemble_model(preprocessor: ColumnTransformer) -> VotingClassifier:
    def make_pipe(classifier) -> Pipeline:
        return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])

    pipe_lr = make_pipe(LogisticRegression())
    pipe_rf = make_pipe(RandomForestClassifier())
    pipe_knn = make_pipe(KNeighborsClassifier())
    return VotingClassifier(
        estimators=[
            ("logistic_regression", pipe_lr),
            ("random_forest", pipe_rf),
            ("knn", pipe_knn),
        ],
        voting="soft",
    )


def preprocess_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    # we only need pollination attempts that have been finished (i.e. have a final
    # status) or are in seed_capsule or later stage
    succesful_status = ["seed_capsule", "seed", "germinated"]
    finished = ~df["ongoing"]
    pollinated_successfully = df["pollination_status"].isin(succesful_status)
    relevant = finished | pollinated_successfully
    df: pd.DataFrame = df[relevant]

    # the boolean columns need a True or False, otherwise training fails
    df.loc[df["hybrid_seed_capsule"].isna(), "hybrid_seed_capsule"] = False
    df.loc[df["hybridgenus_seed_capsule"].isna(), "hybridgenus_seed_capsule"] = False
    df.loc[df["hybrid_pollen_donor"].isna(), "hybrid_pollen_donor"] = False
    df.loc[df["hybridgenus_pollen_donor"].isna(), "hybridgenus_pollen_donor"] = False
    df.loc[df["same_genus"].isna(), "same_genus"] = False
    df.loc[df["same_species"].isna(), "same_species"] = False

    # if we don't have a number of pollination attempts ('count_attempted'), we set it to one
    # if attempt was succesful, we set count_pollinated to one, too; otherwise to zero
    for index, row in df.iterrows():
        if math.isnan(row["count_attempted"]):
            row["count_attempted"] = 1
            row["count_pollinated"] = 1 if row["pollination_status"] in succesful_status else 0
        df.loc[index, :] = row

    # if we don't have count_pollinated...
    #    if not succesful, set to zero
    #    if successful...
    #          set to count_capsules if available
    #         otherwise set to one and...
    #             if count_attempted > 1, set that to one, too

    for index, row in df.iterrows():
        if math.isnan(row["count_pollinated"]):
            if row["pollination_status"] not in succesful_status:
                row["count_pollinated"] = 0
            elif (
                not math.isnan(row["count_capsules"])
                and not row["count_capsules"] > row["count_attempted"]
            ):
                row["count_pollinated"] = row["count_capsules"]

            else:
                row["count_pollinated"] = 1
                if row["count_attempted"] != 1:
                    row["count_attempted"] = 1
        df.loc[index, :] = row

    # a row with count_attempted > 1 is multiplied
    logger.info(f"Shape before: {df.shape}")
    rows = []
    for _, row in df.iterrows():
        for i in range(1, int(row["count_attempted"]) + 1):
            new_row = row.copy()
            new_row["successful_attempt"] = i <= row["count_pollinated"]
            rows.append(new_row)

    df = pd.concat(rows, axis=1, ignore_index=True).T
    logger.info(f"Shape after: {df.shape}")

    target = df["successful_attempt"].astype("int")

    # Remove columns not used in training
    drop_columns = [
        "count_attempted",
        "count_pollinated",
        "count_capsules",
        "pollination_status",
        "ongoing",
        "successful_attempt",
        "location",
    ]
    df = df.drop(drop_columns, axis=1)

    return df, target


async def train_model_for_probability_of_seed_production() -> dict[str, str | float]:
    """Predict whether a pollination attempt is goint to reach SEED status."""
    feature_container = _create_features()
    df_all = await assemble_pollination_data(feature_container=feature_container)
    # make sure we have only the labels we want (not each must be existent, though)
    if set(df_all.pollination_status.unique()) - {
        "seed_capsule",
        "germinated",
        "seed",
        "attempt",
    }:
        raise ValueError("Unexpected pollination status in dataset.")

    df, target = preprocess_data(df_all)

    preprocessor = make_preprocessor(df)
    ensemble = create_ensemble_model(preprocessor)

    # score with kfold split
    metric_name = "f1"
    scores = cross_val_score(
        estimator=ensemble, X=df, y=target, cv=4, scoring=metric_name
    )  # 1 is best, 0 is worst
    metric_value = round(float(scores.mean()), 2)

    # train with whole dataset
    ensemble.fit(X=df, y=target)

    pickle_pipeline(
        pipeline=ensemble,
        feature_container=feature_container,
        prediction_model=PredictionModel.POLLINATION_PROBABILITY,
    )

    from plants.modules.pollination.prediction import predict_pollination

    predict_pollination.pollination_pipeline, predict_pollination.feature_container = None, None

    return {
        "model": PredictionModel.POLLINATION_PROBABILITY,
        "estimator": "Ensemble " + str([e[1][1] for e in ensemble.estimators]),
        "metric_name": metric_name,
        "metric_value": metric_value,
    }
