from __future__ import annotations

import logging
import pickle
from typing import TYPE_CHECKING

from plants import settings
from plants.constants import (
    FILENAME_GERMINATION_DAYS_ESTIMATOR,
    FILENAME_GERMINATION_PROBABILITY_ESTIMATOR,
    FILENAME_PICKLED_POLLINATION_ESTIMATOR,
    FILENAME_RIPENING_DAYS_ESTIMATOR,
)
from plants.modules.pollination.enums import PredictionModel
from plants.shared.message_services import throw_exception

if TYPE_CHECKING:
    from sklearn.ensemble import VotingClassifier, VotingRegressor
    from sklearn.pipeline import Pipeline

    from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
        FeatureContainer,
    )

logger = logging.getLogger(__name__)


def unpickle_pipeline(
    prediction_model: PredictionModel
) -> tuple[Pipeline | VotingRegressor | VotingClassifier, FeatureContainer]:
    # todo async
    if prediction_model == PredictionModel.POLLINATION_PROBABILITY:
        path = settings.paths.path_pickled_ml_models.joinpath(
            FILENAME_PICKLED_POLLINATION_ESTIMATOR
        )
    elif prediction_model == PredictionModel.RIPENING_DAYS:
        path = settings.paths.path_pickled_ml_models.joinpath(FILENAME_RIPENING_DAYS_ESTIMATOR)
    elif prediction_model == PredictionModel.GERMINATION_PROBABILITY:
        path = settings.paths.path_pickled_ml_models.joinpath(
            FILENAME_GERMINATION_PROBABILITY_ESTIMATOR
        )
    elif prediction_model == PredictionModel.GERMINATION_DAYS:
        path = settings.paths.path_pickled_ml_models.joinpath(FILENAME_GERMINATION_DAYS_ESTIMATOR)
    else:
        raise ValueError(f"Unknown prediction model {prediction_model}")

    if not path.is_file():
        throw_exception(f"Pipeline not found at {path.as_posix()}")
    logger.info(f"Unpickling pipeline from {path.as_posix()}.")
    with path.open("rb") as file:
        dump = pickle.load(file)  # noqa: S301
    return dump["pipeline"], dump["feature_container"]


def pickle_pipeline(
    pipeline: Pipeline | VotingRegressor | VotingClassifier,
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
    elif prediction_model == PredictionModel.GERMINATION_PROBABILITY:
        path = settings.paths.path_pickled_ml_models.joinpath(
            FILENAME_GERMINATION_PROBABILITY_ESTIMATOR
        )
    elif prediction_model == PredictionModel.GERMINATION_DAYS:
        path = settings.paths.path_pickled_ml_models.joinpath(FILENAME_GERMINATION_DAYS_ESTIMATOR)
    else:
        raise ValueError(f"Unknown prediction model {prediction_model}")

    logger.info(f"Pickling pipeline to {path.as_posix()}.")
    dump = {"pipeline": pipeline, "feature_container": feature_container}
    with path.open("wb") as file:
        pickle.dump(dump, file)
