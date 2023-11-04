from __future__ import annotations

import logging
import pickle
from typing import TYPE_CHECKING

from plants import settings
from plants.constants import (
    FILENAME_PICKLED_POLLINATION_ESTIMATOR,
    FILENAME_RIPENING_DAYS_ESTIMATOR,
)
from plants.modules.pollination.enums import PredictionModel
from plants.shared.message_services import throw_exception

if TYPE_CHECKING:
    from sklearn.ensemble import VotingRegressor
    from sklearn.pipeline import Pipeline

    from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
        FeatureContainer,
    )


logger = logging.getLogger(__name__)
pollination_pipeline, feature_container = None, None


def _unpickle_pipeline(prediction_model: PredictionModel) -> tuple[Pipeline, FeatureContainer]:
    if prediction_model == PredictionModel.POLLINATION_PROBABILITY:
        path = settings.paths.path_pickled_ml_models.joinpath(
            FILENAME_PICKLED_POLLINATION_ESTIMATOR
        )
    elif prediction_model == PredictionModel.RIPENING_DAYS:
        path = settings.paths.path_pickled_ml_models.joinpath(FILENAME_RIPENING_DAYS_ESTIMATOR)
    else:
        raise ValueError(f"Unknown prediction model {prediction_model}")

    if not path.is_file():
        throw_exception(f"Pipeline not found at {path.as_posix()}")
    logger.info(f"Unpickling pipeline from {path.as_posix()}.")
    with path.open("rb") as file:
        dump = pickle.load(file)  # noqa: S301
    return dump["pipeline"], dump["feature_container"]


def get_probability_of_seed_production_model() -> tuple[Pipeline, FeatureContainer]:
    global pollination_pipeline
    global feature_container
    if pollination_pipeline is None:
        pollination_pipeline, feature_container = _unpickle_pipeline(
            prediction_model=PredictionModel.POLLINATION_PROBABILITY
        )
    return pollination_pipeline, feature_container


def pickle_pipeline(
    pipeline: Pipeline | VotingRegressor,
    feature_container: FeatureContainer,
    prediction_model: PredictionModel,
) -> None:
    """Called from manually executed script, not used in application/frontend/automatically."""
    if prediction_model == PredictionModel.POLLINATION_PROBABILITY:
        path = settings.paths.path_pickled_ml_models.joinpath(
            FILENAME_PICKLED_POLLINATION_ESTIMATOR
        )
    elif prediction_model == PredictionModel.RIPENING_DAYS:
        path = settings.paths.path_pickled_ml_models.joinpath(FILENAME_RIPENING_DAYS_ESTIMATOR)
    else:
        raise ValueError(f"Unknown prediction model {prediction_model}")

    logger.info(f"Pickling pipeline to {path.as_posix()}.")
    dump = {"pipeline": pipeline, "feature_container": feature_container}
    with path.open("wb") as file:
        pickle.dump(dump, file)
