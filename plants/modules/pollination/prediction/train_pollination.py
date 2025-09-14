from __future__ import annotations

import logging

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from plants.modules.pollination.enums import PredictionModel
from plants.modules.pollination.prediction.ml_common import (
    pickle_pipeline,
)
from plants.modules.pollination.prediction.pollination_data import assemble_pollination_data
from plants.modules.pollination.prediction.shared_pollination import validate_and_set_dtypes


logger = logging.getLogger(__name__)


def preprocess_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    # we only need pollination attempts that have been finished (i.e. have a final
    # status) or are in seed_capsule or later stage
    succesful_status = ["seed_capsule", "seed", "germinated"]
    finished = ~df["ongoing"]
    pollinated_successfully = df["pollination_status"].isin(succesful_status)
    relevant = finished | pollinated_successfully
    df = df[relevant]  # type: ignore[assignment]

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
    df_all = await assemble_pollination_data()
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

    clf_lgbm, mean_score_lgbm = train_probability_model_lgbm(df_train=df, ser_targets_train=target)

    pickle_pipeline(
        pipeline=clf_lgbm,  # ensemble,
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
