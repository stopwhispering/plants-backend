import logging
import pickle

from sklearn.pipeline import Pipeline

from ml_helpers.preprocessing.features import FeatureContainer
from plants import config

logger = logging.getLogger(__name__)
FILENAME_PICKLED_POLLINATION_ESTIMATOR = 'pollination_estimator.pkl'
pipeline, feature_container = None, None


def _unpickle_pipeline() -> tuple[Pipeline, FeatureContainer]:
    path = config.path_pickled_ml_models.joinpath(FILENAME_PICKLED_POLLINATION_ESTIMATOR)
    logger.info(f'Unpickling pipeline from {path.as_posix()}.')
    dump = pickle.load(open(path, "rb"))
    if not path.exists():
        raise FileNotFoundError(f'Filename not found: {path.as_posix()}')
    return dump['pipeline'], dump['feature_container']


def get_probability_of_seed_production_model() -> tuple[Pipeline, FeatureContainer]:
    global pipeline
    global feature_container
    if pipeline is None:
        pipeline, feature_container = _unpickle_pipeline()
    return pipeline, feature_container


def pickle_pipeline(pipeline: Pipeline, feature_container: FeatureContainer):
    """called from manually executed script, not used in application/frontend/automatically"""
    path = config.path_pickled_ml_models.joinpath(FILENAME_PICKLED_POLLINATION_ESTIMATOR)
    logger.info(f'Pickling pipeline to {path.as_posix()}.')
    dump = {'pipeline': pipeline,
            'feature_container': feature_container}
    pickle.dump(dump, open(path, "wb"))