from __future__ import annotations

from typing import TYPE_CHECKING

from plants.modules.pollination.enums import PredictionModel
from plants.modules.pollination.prediction.florescence_data import assemble_florescence_data

if TYPE_CHECKING:
    import pandas as pd  # noqa
    from sklearn.base import RegressorMixin  # noqa


async def train_model_for_florescence_probability() -> dict[str, str | float]:
    """Predict whether a plant is going to flower; todo per month? ."""
    # feature_container = create_germination_features()
    # read florescence data (including plants and taxa) plus plants (including taxa) including
    # those that have not yet flowered
    (
        df_florescence,
        df_plant,
        df_event,
    ) = await assemble_florescence_data()  # feature_container=feature_container)
    # df_florescence.to_pickle('/temp/florescence.pkl')
    # df_plant.to_pickle('/temp/plant.pkl')
    a = 1  # noqa
    # df, target = preprocess_data_for_probability_model(df_all)
    #
    # preprocessor = make_preprocessor(df)
    # ensemble = create_germination_probability_ensemble_model(preprocessor)
    #
    # # score with kfold split
    # metric_name = "roc_auc"
    # scores = cross_val_score(estimator=ensemble, X=df, y=target, cv=4, scoring=metric_name)
    # metric_value = round(float(scores.mean()), 2)
    # logger.info(f"Cross-validation score ({metric_name}): {metric_value}")
    #
    # # train with whole dataset
    # try:
    #     ensemble.fit(X=df, y=target)
    # except ValueError as exc:  # raised if NaN in input data
    #     raise TrainingError(msg=str(exc)) from exc
    #
    # pickle_pipeline(
    #     pipeline=ensemble,
    #     feature_container=feature_container,
    #     prediction_model=PredictionModel.GERMINATION_PROBABILITY,
    # )
    #
    # # pylint: disable=import-outside-toplevel
    # from plants.modules.pollination.prediction import predict_germination
    #
    # (
    #     predict_germination.germination_probability_model,
    #     predict_germination.germination_feature_container,
    # ) = None, None

    metric_name = "todo"
    metric_value = 0.0
    estimator = "todo"
    return {
        "model": PredictionModel.FLORESCENCE_PROBABILITY,
        "estimator": estimator,
        "metric_name": metric_name,
        "metric_value": metric_value,
    }
