# note: Use this for development only; for production, the same code (more oer less) is
# in services/ml_model.py

import logging

from sklearn import neighbors

from plants import local_config
from plants.dependencies import get_db
from plants.extensions.db import create_db_engine
from plants.extensions.ml_models import pickle_pipeline
from plants.extensions.orm import init_orm
from plants.scripts.ml.ml_model.ml_data import create_data
from plants.scripts.ml.ml_model.ml_features import ModelType, create_features
from plants.scripts.ml.ml_model.ml_pipeline import create_pipeline
from plants.scripts.ml.ml_model.ml_train import cv_classifier

logging.basicConfig(level=logging.DEBUG, force=True)

init_orm(engine=create_db_engine(local_config.connection_string))
db = next(get_db())


def create_model_for_probability_of_successful_germination():
    """Predict whether a seed is going to germinate, i.e. pollination reaches GERMINATED
    status."""
    # feature_container = create_features(
    # model_type=ModelType.POLLINATION_TO_GERMINATION)
    # df = create_data(feature_container=feature_container)
    # todo...


def train_model_for_probability_of_seed_production():
    """Predict whether a pollination attempt is goint to reach SEED status."""
    feature_container = create_features(model_type=ModelType.POLLINATION_TO_SEED)
    df = create_data(feature_container=feature_container)
    # make sure we have only the labels we want (not each must be existent, though)
    if set(df.pollination_status.unique()) - {
        "seed_capsule",
        "germinated",
        "seed",
        "attempt",
    }:
        raise ValueError("Unexpected pollination_status values")
    y = df["pollination_status"].apply(
        lambda s: 1 if s in {"seed_capsule", "seed", "germinated"} else 0
    )
    x = df[feature_container.get_columns()]

    # find suitable classifier, optimize hyperparameters
    # _try_classifiers(x, y, feature_container)
    # _optimize_knn_classifier(x, y, feature_container)
    # _optimize_randomforest_classifier(x, y, feature_container)

    # train directly on full dataset with optimized hyperparams
    params_knn = {
        "algorithm": "ball_tree",
        "leaf_size": 20,
        "n_neighbors": 10,
        "p": 2,
        "weights": "distance",
    }
    model = neighbors.KNeighborsClassifier(**params_knn)
    # params_rfc = {'n_estimators': 5, 'min_samples_split': 0.01, 'max_features': None}
    # model = ensemble.RandomForestClassifier(**params_rfc)

    pipeline = create_pipeline(feature_container=feature_container, model=model)

    # show f1 cv score
    cv_classifier(x, y, pipeline)

    # fit with full dataset
    pipeline.fit(x, y)
    pickle_pipeline(pipeline=pipeline, feature_container=feature_container)


train_model_for_probability_of_seed_production()
