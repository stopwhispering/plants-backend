from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor, VotingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from plants.exceptions import TrainingError
from plants.modules.pollination.enums import PredictionModel
from plants.modules.pollination.prediction.ml_common import pickle_pipeline
from plants.modules.pollination.prediction.ml_helpers.log_results import log_results
from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
    Feature,
    FeatureContainer,
    Scale,
)
from plants.modules.pollination.prediction.pollination_data import assemble_pollination_data
from plants.modules.pollination.prediction.predict_ripening import logger

if TYPE_CHECKING:
    from sklearn.base import RegressorMixin


def _create_features() -> FeatureContainer:
    """Create a features container for a specific model to be trained."""
    features = [
        # todo this is useless, replace or remove
        Feature(column="location", scale=Scale.NOMINAL),
        Feature(column="genus_seed_capsule", scale=Scale.NOMINAL),
        Feature(column="species_seed_capsule", scale=Scale.NOMINAL),
        Feature(column="genus_pollen_donor", scale=Scale.NOMINAL),
        Feature(column="species_pollen_donor", scale=Scale.NOMINAL),
        Feature(column="hybrid_seed_capsule", scale=Scale.BOOLEAN),
        Feature(column="hybridgenus_seed_capsule", scale=Scale.BOOLEAN),
        Feature(column="hybrid_pollen_donor", scale=Scale.BOOLEAN),
        Feature(column="hybridgenus_pollen_donor", scale=Scale.BOOLEAN),
        Feature(column="same_genus", scale=Scale.BOOLEAN),
        Feature(column="same_species", scale=Scale.BOOLEAN),
    ]
    # todo: pollination_timestamp (morning, evening, etc.) once enough data is available
    return FeatureContainer(features=features)


def multiply_rows_by_capsule_count(df: pd.DataFrame) -> pd.DataFrame:
    # a row with count_capsules > 1 is multiplied
    # print('Shape before: ', df.shape)
    rows = []
    for _, row in df.iterrows():
        rows.extend([row] * int(row["count_capsules"]))
    return pd.concat(rows, axis=1, ignore_index=True).T


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    # we only need successful pollination attempts that made it to the seed or germinated status
    df = df[df["pollination_status"].isin(["seed", "germinated"])]  # type: ignore[assignment]

    # Since harvest_date is basically what we want to predict, and there is no way to derive
    # that feature from any other feature, we can remove
    # all rows with missing harvest_date
    # the same applies to pollinated_at
    df = df[~df["harvest_date"].isna()]  # type: ignore[assignment]
    df = df[~df["pollinated_at"].isna()]  # type: ignore[assignment]

    # we can use count_pollinated to infer count_capsules (more or less)
    df.loc[df["count_capsules"].isna(), "count_capsules"] = df.loc[
        df["count_capsules"].isna(), "count_pollinated"
    ]

    # we can use rows with a count_capsules of > 1 to multiply these rows. if that
    # feature is missing, we assume a count of 1.
    df.loc[df["count_capsules"].isna(), "count_capsules"] = 1

    # multiply rows, i.e. apply count_capsules
    df = multiply_rows_by_capsule_count(df)

    # compute Target (number of days)
    # not relevant for notebook
    df["pollinated_at"] = df["pollinated_at"].apply(lambda d: d.date())

    # compute ripening period in days
    df["ripening_days"] = (df["harvest_date"] - df["pollinated_at"]).apply(
        lambda timedelta: timedelta.days
    )

    # in some cases, we don't have info about the  hybrid status of one of the plants
    # we set them to false as a default
    df.loc[df["hybrid_seed_capsule"].isna(), "hybrid_seed_capsule"] = False
    df.loc[df["hybridgenus_seed_capsule"].isna(), "hybridgenus_seed_capsule"] = False
    df.loc[df["hybrid_pollen_donor"].isna(), "hybrid_pollen_donor"] = False
    df.loc[df["hybridgenus_pollen_donor"].isna(), "hybridgenus_pollen_donor"] = False

    return df


def make_preprocessor(df: pd.DataFrame) -> ColumnTransformer:
    categorical_features = [
        "location",
        "genus_seed_capsule",
        "species_seed_capsule",
        "genus_pollen_donor",
        "species_pollen_donor",
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


def create_ensemble_model(preprocessor: ColumnTransformer) -> VotingRegressor:
    def make_pipe(regressor: RegressorMixin) -> Pipeline:
        return Pipeline([("preprocessor", preprocessor), ("regressor", regressor)])

    pipe_linear = make_pipe(LinearRegression())
    pipe_rfr = make_pipe(RandomForestRegressor())
    pipe_knn = make_pipe(KNeighborsRegressor())
    return VotingRegressor(
        estimators=[("linear", pipe_linear), ("random_forest", pipe_rfr), ("knn", pipe_knn)]
    )


async def train_model_for_ripening_days() -> dict[str, str | float]:
    """Predict whether a pollination attempt is goint to reach SEED status."""
    feature_container = _create_features()
    df_all = await assemble_pollination_data()

    df = preprocess_data(df_all)

    preprocessor = make_preprocessor(df)
    ensemble = create_ensemble_model(preprocessor)

    # score with kfold split
    metric_name = "r2"
    scores = cross_val_score(
        estimator=ensemble, X=df, y=df["ripening_days"], cv=4, scoring=metric_name
    )  # best is 1.0; 0.0 would be ~average
    metric_value = round(float(scores.mean()), 2)

    # train with whole dataset
    try:
        ensemble.fit(X=df, y=df["ripening_days"])
    except ValueError as exc:  # raised if NaN in input data
        raise TrainingError(msg=str(exc)) from exc

    pickle_pipeline(
        pipeline=ensemble,
        feature_container=feature_container,
        prediction_model=PredictionModel.RIPENING_DAYS,
    )

    # pylint: disable=import-outside-toplevel
    from plants.modules.pollination.prediction import predict_ripening

    predict_ripening.ripening_days_regressor, predict_ripening.feature_container = None, None

    notes = f"Training data has {len(df)} rows."

    log_results(
        model_category=PredictionModel.RIPENING_DAYS,
        estimator="Ensemble " + str([e[1][1] for e in ensemble.estimators]),
        metrics={metric_name: metric_value},
        notes=notes,
        training_stats={
            "n_training_rows": int(len(df)),
        },
    )

    return {
        "model": PredictionModel.RIPENING_DAYS,
        "estimator": "Ensemble " + str([e[1][1] for e in ensemble.estimators]),
        "metric_name": metric_name,
        "metric_value": metric_value,
        "notes": notes,
    }
