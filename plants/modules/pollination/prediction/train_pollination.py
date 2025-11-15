from __future__ import annotations

import logging
from contextlib import contextmanager

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
import shap
import io
from fastapi.responses import StreamingResponse

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.pyplot as plt
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


def generate_shap_values_for_model(
        model: lgb.LGBMClassifier,
        df: pd.DataFrame,
) -> tuple[shap._explanation.Explanation, pd.DataFrame]:  # noqa
    """compute SHAP values from final deployed model for best model explainability;
    shap values and training data are returned and to be stored in app state for later use"""

    df_preprocessed = preprocess_data_lgbm(df)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer(df_preprocessed)

    return shap_values, df_preprocessed


async def train_model_for_probability_of_seed_production(
) -> tuple[dict[str, str | float], shap._explanation.Explanation, pd.DataFrame]:  # noqa
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
    share_positive = round(target.sum() * 100 / len(target), 2)
    notes += (
        f"Training data has {len(df)} rows with {target.sum()} positive labels "
        f"({share_positive} %)."
    )

    clf_lgbm, mean_score_lgbm = train_probability_model_lgbm(df_train=df, ser_targets_train=target)

    pickle_pipeline(
        pipeline=clf_lgbm,  # ensemble,
        prediction_model=PredictionModel.POLLINATION_PROBABILITY,
    )

    # comute SHAP values from final deployed model for best model explainability
    # get the summary image as a StreamingResponse
    # (for feature importance stability we could also average over the models from CV folds)
    shap_values, df_preprocessed = generate_shap_values_for_model(clf_lgbm, df)

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
    }, shap_values, df_preprocessed


@contextmanager
def isolated_matplotlib():
    """Create a temporary isolated pyplot environment."""
    # save current pyplot state
    original_figures = plt.get_fignums()
    try:
        yield
    finally:
        # close any new figures created inside the context
        new_figures = [f for f in plt.get_fignums() if f not in original_figures]
        for fnum in new_figures:
            plt.close(fnum)


def generate_shap_summary_plot(shap_values, df_preprocessed) -> StreamingResponse:
    """Generate SHAP summary plot as StreamingResponse."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # SHAP expects plt.gcf(), so temporarily override pyplot
    plt_backup = plt.gcf
    plt.gcf = lambda: fig  # override plt.gcf() to return our fig

    try:
        shap.summary_plot(shap_values, df_preprocessed, show=False)

        buf = io.BytesIO()
        canvas = FigureCanvas(fig)
        canvas.print_png(buf)
        buf.seek(0)
    finally:
        # Restore plt.gcf
        plt.gcf = plt_backup
        plt.close(fig)

    return StreamingResponse(buf, media_type="image/png")


def generate_lgbm_feature_importance_gain_plot(clf_lgbm) -> StreamingResponse:
    """Generate LGBM Feature Importance (Gain) plot as StreamingResponse."""
    fig, ax = plt.subplots(figsize=(18, 6))
    lgb.plot_importance(
        clf_lgbm,
        importance_type='gain',
        ax=ax,
        title='LightGBM Feature Importance (Gain)'
    )

    buf = io.BytesIO()
    canvas = FigureCanvas(fig)
    canvas.print_png(buf)
    buf.seek(0)
    plt.close(fig)

    return StreamingResponse(buf, media_type="image/png")


def generate_lgbm_feature_importance_split_plot(clf_lgbm) -> StreamingResponse:
    """Generate LGBM Feature Importance (Split) plot as StreamingResponse."""
    fig, ax = plt.subplots(figsize=(18, 6))
    lgb.plot_importance(
        clf_lgbm,
        importance_type='split',
        ax=ax,
        title='LightGBM Feature Importance (Split)'
    )

    buf = io.BytesIO()
    canvas = FigureCanvas(fig)
    canvas.print_png(buf)
    buf.seek(0)
    plt.close(fig)

    return StreamingResponse(buf, media_type="image/png")
