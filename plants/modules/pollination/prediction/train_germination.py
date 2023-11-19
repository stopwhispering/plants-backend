from __future__ import annotations

from typing import TYPE_CHECKING

from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
    VotingClassifier,
    VotingRegressor,
)
from sklearn.impute import KNNImputer
from sklearn.linear_model import Lasso, LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from plants.exceptions import TrainingError
from plants.modules.pollination.enums import PredictionModel
from plants.modules.pollination.prediction.ml_common import pickle_pipeline
from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
    Feature,
    FeatureContainer,
    Scale,
)
from plants.modules.pollination.prediction.predict_ripening import logger
from plants.modules.pollination.prediction.seed_planting_data import assemble_seed_planting_data

if TYPE_CHECKING:
    import pandas as pd
    from sklearn.base import RegressorMixin


def create_germination_features() -> FeatureContainer:
    """Create a features container for a specific model to be trained."""
    features = [
        # todo this is useless, replace or remove
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
        # Feature(column="sterilized", scale=Scale.BOOLEAN),
        # Feature(column="soaked", scale=Scale.BOOLEAN),
        # Feature(column="count_planted", scale=Scale.METRIC),
        # Feature(column="soil_name", scale=Scale.NOMINAL),
        # Feature(column="pollination_count_attempted", scale=Scale.METRIC),
        # Feature(column="pollination_count_pollinated", scale=Scale.METRIC),
        # Feature(column="pollination_count_capsules", scale=Scale.METRIC),
        # Feature(column="pollination_seed_capsule_length", scale=Scale.METRIC),
        # Feature(column="pollination_seed_count", scale=Scale.METRIC),
        # Feature(column="pollination_seed_width", scale=Scale.METRIC),
        # Feature(column="pollination_seed_length", scale=Scale.METRIC),
        # Feature(column="pollination_type", scale=Scale.NOMINAL_BIVALUE),
        # Feature(column="planted_on", scale=Scale.BOOLEAN),
        # Feature(column="germinated_first_on", scale=Scale.BOOLEAN),
        # Feature(column="seed_planting_status", scale=Scale.NOMINAL),
    ]
    # todo: pollination_timestamp (morning, evening, etc.) once enough data is available
    return FeatureContainer(features=features)


#
# def multiply_rows_by_capsule_count(df: pd.DataFrame) -> pd.DataFrame:
#     # a row with count_capsules > 1 is multiplied
#     # print('Shape before: ', df.shape)
#     rows = []
#     for _, row in df.iterrows():
#         rows.extend([row] * int(row["count_capsules"]))
#     return pd.concat(rows, axis=1, ignore_index=True).T


def preprocess_data_for_probability_model(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    # Drop obviously irrelevant columns
    irrelevant_columns = [
        "id",
        "seed_capsule_plant_id",
        "pollen_donor_plant_id",
        "label_color",
        # 'id_pollen_donor.1',
        "count_attempted",
        "florescence_id",
        "seed_capsule_width",
        "comment",
        "seed_description",
        "seed_capsule_description",
        "last_updated_at",
        "last_update_context",
        "created_at",
        "last_update_at",
        "creation_at",
        "creation_at_context",
        "id_seed_capsule",
        "taxon_id_seed_capsule",
        "id_pollen_donor",
        "taxon_id_pollen_donor",
        # 'id_seed_capsule.1',
        "count_pollinated",
        "count_capsules",
        "pollinated_at",
        "pollination_id",
        "ongoing",
        "comment_pollination",
        "pollination_status",
        "harvest_date",
    ]
    maybe_not_drop_later = ["pollen_quality", "pollen_type", "location", "seed_count"]
    df = df.drop(irrelevant_columns + maybe_not_drop_later, axis=1)

    # Remove irrelevant Rows
    # Rows with status 'planted' are still ongoing, we remove them
    mask_ongoing: pd.Series = df["status"] == "planted"
    df = df[~mask_ongoing]  # type: ignore[assignment]

    # As long as we have a vast or almost majority of legacy data with no
    # sterilized/soaked/covered/soil_id/count_germinated/count_planted
    # information, we need to discard those columns
    df = df.drop(
        [
            "sterilized",
            "soaked",
            "covered",
            "soil_id",
            "count_germinated",
            "count_planted",
        ],
        axis=1,
    )

    mask_germinated = df["status"] == "germinated"
    mask_abandoned = ~mask_germinated

    # target labels
    # make sure we don't have inconsistent data - abandoned with a germination day
    mask_has_germination_day = ~df["germinated_first_on"].isna()
    if len(df[mask_abandoned & mask_has_germination_day]):
        raise ValueError(
            f"Inconsistent data: {len(df[mask_abandoned & mask_has_germination_day])} "
            f"abandoned seed plantings with germination day"
        )

    # We can simply use the status as our target
    target: pd.Series = df["status"].map({"germinated": 1, "abandoned": 0})
    if target.isna().sum():
        raise ValueError(f"NaN in target: {target.isna().sum()}")
    df = df.drop(["status"], axis=1)

    return df, target


def preprocess_data_for_days_model(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    # Drop obviously irrelevant columns
    irrelevant_columns = [
        "id",
        "seed_capsule_plant_id",
        "pollen_donor_plant_id",
        "label_color",
        # 'id_pollen_donor.1',
        "count_attempted",
        "florescence_id",
        "seed_capsule_width",
        "comment",
        "seed_description",
        "seed_capsule_description",
        "last_updated_at",
        "last_update_context",
        "created_at",
        "last_update_at",
        "creation_at",
        "creation_at_context",
        "id_seed_capsule",
        "taxon_id_seed_capsule",
        "id_pollen_donor",
        "taxon_id_pollen_donor",
        # 'id_seed_capsule.1',
        "count_pollinated",
        "count_capsules",
        "pollinated_at",
        "pollination_id",
        "ongoing",
        "comment_pollination",
        "pollination_status",
        "harvest_date",
    ]
    maybe_not_drop_later = ["pollen_quality", "pollen_type", "location", "seed_count"]
    df = df.drop(irrelevant_columns + maybe_not_drop_later, axis=1)

    # Remove irrelevant Rows
    # Rows with status 'planted' are still ongoing, we remove them
    mask_ongoing: pd.Series = df["status"] == "planted"
    df = df[~mask_ongoing]  # type: ignore[assignment]

    # As long as we have a vast or almost majority of legacy data with no
    # sterilized/soaked/covered/soil_id/count_germinated/count_planted
    # information, we need to discard those columns
    df = df.drop(
        [
            "sterilized",
            "soaked",
            "covered",
            "soil_id",
            "count_germinated",
            "count_planted",
        ],
        axis=1,
    )

    # target labels
    # we only care about successful seed plantings
    df = df[df["status"] == "germinated"]  # type: ignore[assignment]

    # the target label is the number of days, computed as germination day - planted day; discard rows with one of them missing
    df = df[~df["germinated_first_on"].isna()]  # type: ignore[assignment]

    # # both columns are string-formatted; convert them to date objects
    # ser_germinated = df['germinated_first_on'].apply(
    #     lambda dstr: datetime.datetime.strptime(dstr, "%Y-%m-%d"))
    # ser_planted = df['planted_on'].apply(lambda dstr: datetime.datetime.strptime(dstr, "%Y-%m-%d"))

    # compute germination period in days
    target: pd.Series = (df["germinated_first_on"] - df["planted_on"]).apply(  # type: ignore[assignment]
        lambda timedelta: timedelta.days
    )

    return df, target


def make_preprocessor(df: pd.DataFrame) -> ColumnTransformer:
    categorical_features = [
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
    metric_features = ["seed_capsule_length", "seed_length", "seed_width"]

    dropped = [
        c for c in df.columns if c not in categorical_features + boolean_features + metric_features
    ]
    logger.info(f"Columns not used for prediction:\n{dropped}")

    # Preprocessing Pipeline for metric features:
    # - Imputation
    # - Standardizing (for linear models)
    metric_pipeline = Pipeline(
        [("imputation", KNNImputer(n_neighbors=2)), ("scaling", StandardScaler())]
    )

    one_hot_encoder = OneHotEncoder(
        handle_unknown="ignore",  # all zeros for NaN
        sparse_output=False,
    )

    return ColumnTransformer(
        transformers=[
            ("cat", one_hot_encoder, categorical_features),
            ("bool", "passthrough", boolean_features),
            ("metric", metric_pipeline, metric_features),
        ],
        remainder="drop",
    )


def create_germination_probability_ensemble_model(
    preprocessor: ColumnTransformer
) -> VotingClassifier:
    def make_pipe(regressor: RegressorMixin) -> Pipeline:
        return Pipeline(
            [("preprocessor", preprocessor), ("pca", PCA(n_components=9)), ("regressor", regressor)]
        )

    pipe_linear = make_pipe(LogisticRegression())
    pipe_rfr = make_pipe(RandomForestClassifier())
    pipe_knn = make_pipe(KNeighborsClassifier())
    return VotingClassifier(
        estimators=[("linear", pipe_linear), ("random_forest", pipe_rfr), ("knn", pipe_knn)],
        voting="soft",
    )


def create_germination_days_ensemble_model(preprocessor: ColumnTransformer) -> VotingRegressor:
    def make_pipe(regressor: RegressorMixin) -> Pipeline:
        return Pipeline([("preprocessor", preprocessor), ("regressor", regressor)])

    pipe_linear = make_pipe(Lasso())  # Linear Regression with L1 Regularization
    pipe_rfr = make_pipe(RandomForestRegressor())
    pipe_knn = make_pipe(KNeighborsRegressor(n_neighbors=2))
    return VotingRegressor(
        estimators=[("linear", pipe_linear), ("random_forest", pipe_rfr), ("knn", pipe_knn)]
    )


async def train_model_for_germination_probability() -> dict[str, str | float]:
    """Predict whether a seed planting is going to reach GERMINATED status."""
    feature_container = create_germination_features()
    df_all = await assemble_seed_planting_data(feature_container=feature_container)

    df, target = preprocess_data_for_probability_model(df_all)

    preprocessor = make_preprocessor(df)
    ensemble = create_germination_probability_ensemble_model(preprocessor)

    # score with kfold split
    metric_name = "roc_auc"
    scores = cross_val_score(estimator=ensemble, X=df, y=target, cv=4, scoring=metric_name)
    metric_value = round(float(scores.mean()), 2)
    logger.info(f"Cross-validation score ({metric_name}): {metric_value}")

    # train with whole dataset
    try:
        ensemble.fit(X=df, y=target)
    except ValueError as e:  # raised if NaN in input data
        raise TrainingError(msg=str(e)) from e

    pickle_pipeline(
        pipeline=ensemble,
        feature_container=feature_container,
        prediction_model=PredictionModel.GERMINATION_PROBABILITY,
    )

    from plants.modules.pollination.prediction import predict_germination

    (
        predict_germination.germination_probability_model,
        predict_germination.germination_feature_container,
    ) = None, None

    return {
        "model": PredictionModel.GERMINATION_PROBABILITY,
        "estimator": "Ensemble " + str([e[1][1] for e in ensemble.estimators]),
        "metric_name": metric_name,
        "metric_value": metric_value,
    }


async def train_model_for_germination_days() -> dict[str, str | float]:
    """Predict how long a seed takes to germinate (assuming germination is successful)."""
    feature_container = create_germination_features()
    df_all = await assemble_seed_planting_data(feature_container=feature_container)

    df, target = preprocess_data_for_days_model(df_all)

    preprocessor = make_preprocessor(df)
    ensemble = create_germination_days_ensemble_model(preprocessor)

    # score with kfold split
    metric_name = "r2"
    scores = cross_val_score(estimator=ensemble, X=df, y=target, cv=4, scoring=metric_name)
    metric_value = round(float(scores.mean()), 2)
    logger.info(f"Cross-validation score ({metric_name}): {metric_value}")

    # train with whole dataset
    try:
        ensemble.fit(X=df, y=target)
    except ValueError as e:  # raised if NaN in input data
        raise TrainingError(msg=str(e)) from e

    pickle_pipeline(
        pipeline=ensemble,
        feature_container=feature_container,
        prediction_model=PredictionModel.GERMINATION_DAYS,
    )

    from plants.modules.pollination.prediction import predict_germination

    predict_germination.germination_days_model, predict_germination.germination_days_container = (
        None,
        None,
    )

    return {
        "model": PredictionModel.GERMINATION_DAYS,
        "estimator": "Ensemble " + str([e[1][1] for e in ensemble.estimators]),
        "metric_name": metric_name,
        "metric_value": metric_value,
    }
