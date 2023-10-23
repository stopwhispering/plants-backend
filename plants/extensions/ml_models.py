from __future__ import annotations

import logging
import pickle
from typing import TYPE_CHECKING

from plants import settings
from plants.constants import FILENAME_PICKLED_POLLINATION_ESTIMATOR
from plants.shared.message_services import throw_exception

if TYPE_CHECKING:
    from sklearn.pipeline import Pipeline

    from plants.modules.pollination.ml_helpers.preprocessing.features import FeatureContainer


logger = logging.getLogger(__name__)
pipeline, feature_container = None, None


def _unpickle_pipeline() -> tuple[Pipeline, FeatureContainer]:
    path = settings.paths.path_pickled_ml_models.joinpath(FILENAME_PICKLED_POLLINATION_ESTIMATOR)
    if not path.is_file():
        throw_exception(f"Pipeline not found at {path.as_posix()}")
    logger.info(f"Unpickling pipeline from {path.as_posix()}.")
    with path.open("rb") as file:
        dump = pickle.load(file)
    return dump["pipeline"], dump["feature_container"]


def get_probability_of_seed_production_model() -> tuple[Pipeline, FeatureContainer]:
    global pipeline
    global feature_container
    if pipeline is None:
        pipeline, feature_container = _unpickle_pipeline()
    return pipeline, feature_container


def pickle_pipeline(pipeline: Pipeline, feature_container: FeatureContainer) -> None:
    """Called from manually executed script, not used in application/frontend/automatically."""
    path = settings.paths.path_pickled_ml_models.joinpath(FILENAME_PICKLED_POLLINATION_ESTIMATOR)
    logger.info(f"Pickling pipeline to {path.as_posix()}.")
    dump = {"pipeline": pipeline, "feature_container": feature_container}
    with path.open("wb") as file:
        pickle.dump(dump, file)
