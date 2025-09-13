from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupKFold, cross_val_score, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

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
from plants.modules.pollination.prediction.shared_pollination import validate_and_set_dtypes

if TYPE_CHECKING:
    from sklearn.base import BaseEstimator, ClassifierMixin

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


def to_bool(x):
    return x.astype("bool")


def to_float(x):
    return x.astype("float")


def to_category(x):
    return x.astype("category")


def make_preprocessor(
    df: pd.DataFrame,
    accept_nan: bool,
    one_hot_encode: bool,
) -> ColumnTransformer:
    # see get_data() in predict_pollination.py for the features used in prediction, todo unify
    categorical_features = [
        # "location",
        "genus_seed_capsule",
        "species_seed_capsule",
        "genus_pollen_donor",
        "species_pollen_donor",
        "pollen_type",
        "pollen_quality",
        # "seed_capsule_plant_id_as_cat",  # currently making model worse
        # "pollen_donor_plant_id_as_cat",  # currently making model worse
    ]

    boolean_features = [
        "hybrid_seed_capsule",
        "hybridgenus_seed_capsule",
        "hybrid_pollen_donor",
        "hybridgenus_pollen_donor",
        "same_genus",
        "same_species",
        "same_plant",
    ]

    # see also estimator init arguments
    numeric_features = [
        "pollinated_at_hour_sin",
        "pollinated_at_hour_cos",
    ]

    dropped = [
        c for c in df.columns if c not in categorical_features + boolean_features + numeric_features
    ]
    logger.info(f"Columns not used for prediction:\n{dropped}")

    missing = [
        c for c in categorical_features + boolean_features + numeric_features if c not in df.columns
    ]
    if missing:
        raise ValueError(f"Missing:\n{missing}")

    if one_hot_encode:
        one_hot_encoder = OneHotEncoder(
            handle_unknown="ignore",  # all zeros for unknown
            sparse_output=False,
        )
        cat_transformer = ("cat", one_hot_encoder, categorical_features)
    else:
        category_transformer = FunctionTransformer(to_category, validate=False)

        cat_transformer = ("cat", category_transformer, categorical_features)
        # cat = ("cat", 'passthrough', categorical_features)

    if accept_nan:
        numeric_transformer = (
            "numeric",
            FunctionTransformer(to_float, validate=False),
            numeric_features,
        )
    else:
        imputer = SimpleImputer(strategy="mean")
        numeric_transformer = ("numeric", imputer, numeric_features)

    # for whatever reason, we need to explicitly convert everything explicitly
    bool_transformer = (
        "bool",
        FunctionTransformer(to_bool, validate=False),
        boolean_features,
    )

    return ColumnTransformer(
        transformers=[
            cat_transformer,
            bool_transformer,
            numeric_transformer,
        ],
        remainder="drop",
    ).set_output(transform="pandas")


def create_ensemble_model(df: pd.DataFrame) -> VotingClassifier:
    def make_pipe(classifier: ClassifierMixin, preprocessor: ColumnTransformer) -> Pipeline:
        return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])

    # pipe_lr = make_pipe(LogisticRegression())
    preprocessor_rf: ColumnTransformer = make_preprocessor(df, accept_nan=True, one_hot_encode=True)
    pipe_rf = make_pipe(RandomForestClassifier(), preprocessor_rf)

    preprocessor_lgbm: ColumnTransformer = make_preprocessor(
        df, accept_nan=True, one_hot_encode=True
    )

    params_lgbm = {
        # "max_depth": 10,  # default: -1 seems optimal
        # "colsample_bytree": 0.4,  # default: 1 seems optimal
        "n_estimators": 1500,  # default: 100 (no early stoppin here for simplicity)
        # "learning_rate": 0.10,  # default: 0.1 seems optimal
        "objective": "binary",  # default: binary (log-loss)
        # "verbose": -1,
    }
    clf = lgb.LGBMClassifier(**params_lgbm)
    pipe_lgbm = make_pipe(clf, preprocessor_lgbm)

    preprocessor_knn: ColumnTransformer = make_preprocessor(
        df, accept_nan=False, one_hot_encode=True
    )
    params_knn = {
        "n_neighbors": 5,  # default: 5 seems optimal
        "weights": "uniform",  # default: uniform seems optimal
    }
    pipe_knn = make_pipe(KNeighborsClassifier(**params_knn), preprocessor_knn)

    return VotingClassifier(
        estimators=[
            # ("logistic_regression", pipe_lr),
            ("random_forest", pipe_rf),
            ("knn", pipe_knn),
            ("lightgbm", pipe_lgbm),
        ],
        voting="soft",  # 'hard' (majority voting) or 'soft' (argmax of the sums of the
        # predicted probabilities)
    )


def preprocess_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    # we only need pollination attempts that have been finished (i.e. have a final
    # status) or are in seed_capsule or later stage
    succesful_status = ["seed_capsule", "seed", "germinated"]
    finished = ~df["ongoing"]
    pollinated_successfully = df["pollination_status"].isin(succesful_status)
    relevant = finished | pollinated_successfully
    df = df[relevant]  # type: ignore[assignment]

    # the boolean columns need a True or False, otherwise training fails
    df.loc[df["hybrid_seed_capsule"].isna(), "hybrid_seed_capsule"] = False
    df.loc[df["hybridgenus_seed_capsule"].isna(), "hybridgenus_seed_capsule"] = False
    df.loc[df["hybrid_pollen_donor"].isna(), "hybrid_pollen_donor"] = False
    df.loc[df["hybridgenus_pollen_donor"].isna(), "hybridgenus_pollen_donor"] = False
    df.loc[df["same_genus"].isna(), "same_genus"] = False
    df.loc[df["same_species"].isna(), "same_species"] = False

    ser_success = df['pollination_status'].isin(succesful_status)
    # Remove columns not allowed in training to avoid data leakage
    drop_columns = [
        "count_pollinated",
        "count_capsules",
        "pollination_status",
        "ongoing",
    ]
    df = df.drop(drop_columns, axis=1)

    return df, ser_success


def preprocess_data_lgbm(
        df: pd.DataFrame
) -> pd.DataFrame:
    df = df.copy()
    return validate_and_set_dtypes(df)


def train_probability_model_lgbm(
        df_train: pd.DataFrame,
        ser_targets_train: pd.Series,
) -> tuple[lgb.LGBMClassifier, float]:

    params_lgbm = {
        # "max_depth": 10,  # default: -1
        # "colsample_bytree": 0.4,  # default: 1
        "n_estimators": 1500,  # default: 100 (early stopping))
        # "learning_rate": 0.10,  # default: 0.1
        "objective": "binary",  # default: binary (log-loss)
        "verbose": -1,
    }

    splits = StratifiedKFold(n_splits=4, shuffle=True, random_state=42).split(df_train, ser_targets_train)
    best_iterations, fold_scores = [], []
    for fold_no, (train_idx, val_idx) in enumerate(splits):
        logger.info(f"Fold {fold_no}")
        df_train_current_fold = df_train.iloc[train_idx]
        df_val_current_fold = df_train.iloc[val_idx]
        ser_targets_train_current_fold = ser_targets_train.iloc[train_idx]
        ser_targets_val_current_fold = ser_targets_train.iloc[val_idx]

        df_train_current_fold_processed = preprocess_data_lgbm(df_train_current_fold)
        df_val_current_fold_processed = preprocess_data_lgbm(df_val_current_fold)
        early_stopping_callback = lgb.early_stopping(
            150, verbose=False
        )
        clf = lgb.LGBMClassifier(**params_lgbm)
        clf.fit(
            X=df_train_current_fold_processed,
            y=ser_targets_train_current_fold,
            callbacks=[early_stopping_callback],
            eval_set=[(df_val_current_fold_processed, ser_targets_val_current_fold)],
            eval_metric="auc",
        )

        best_iterations.append(clf.best_iteration_)
        fold_scores.append(clf.best_score_["valid_0"]["auc"])
        logger.info(f"Best iteration: {best_iterations[-1]}, score: {fold_scores[-1] :.2f}")

    mean_best_iteration = int(np.mean(best_iterations))
    mean_score = round(float(np.mean(fold_scores)), 2)
    logger.info(f"Mean best iteration: {mean_best_iteration}, mean score: {mean_score}")

    # retrain on full data
    df_train_processed = preprocess_data_lgbm(df_train)
    params_lgbm["n_estimators"] = int(mean_best_iteration * 1.1)
    clf = lgb.LGBMClassifier(**params_lgbm)
    clf.fit(
        X=df_train_processed,
        y=ser_targets_train,
    )

    return clf, mean_score


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

    # ensemble = create_ensemble_model(df=df)

    notes = ""
    notes += (
        f"Training data has {len(df)} rows with {target.sum()} positive labels "
        f"({round(target.sum() / len(target), 2) * 100} %)."
    )

    # score with kfold split
    clf_lgbm, mean_score_lgbm = train_probability_model_lgbm(df_train=df, ser_targets_train=target)
    # metric_name = "roc_auc"  # "f1"
    # scores = cross_val_score(
    #     estimator=ensemble, X=df, y=target, cv=4, scoring=metric_name
    # )  # 1 is best, 0 is worst
    # metric_value = round(float(scores.mean()), 2)

    # # train with whole dataset
    # ensemble.fit(X=df, y=target)

    pickle_pipeline(
        pipeline=clf_lgbm,  # ensemble,
        feature_container=feature_container,  # todo remove
        prediction_model=PredictionModel.POLLINATION_PROBABILITY,
    )

    # remove old models from memory to have them reloaded upon next prediction
    # pylint: disable=import-outside-toplevel
    from plants.modules.pollination.prediction import predict_pollination
    predict_pollination.pollination_pipeline, predict_pollination.feature_container = None, None

    return {
        "model": PredictionModel.POLLINATION_PROBABILITY,
        # "estimator": "Ensemble " + str([e[1][1] for e in ensemble.estimators]),
        "estimator": str(clf_lgbm),
        "metric_name": "roc_auc",
        "metric_value": mean_score_lgbm,
        "notes": notes,
    }
