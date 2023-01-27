import numpy as np
import sqlalchemy
import pandas as pd
from sklearn import neighbors
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.utils._testing import ignore_warnings  # noqa
from sqlalchemy.orm import Session

from ml_helpers.preprocessing.features import (FeatureContainer, Scale, Feature)
from plants import local_config
from plants.extensions.db import create_db_engine
from plants.extensions.ml_models import pickle_pipeline
from plants.modules.plant.models import Plant
from plants.modules.pollination.models import Pollination, Florescence
from plants.modules.taxon.models import Taxon


def _create_pipeline(feature_container: FeatureContainer, model: BaseEstimator):
    nominal_features = feature_container.get_columns(scale=Scale.NOMINAL)  # noqa
    nominal_bivalue_features = feature_container.get_columns(scale=Scale.NOMINAL_BIVALUE)
    boolean_features = feature_container.get_columns(scale=Scale.BOOLEAN)
    ordinal_features = feature_container.get_columns(scale=Scale.ORDINAL)
    if ordinal_features:
        raise NotImplementedError('Ordinal features are not supported yet.')
    metric_features = feature_container.get_columns(scale=Scale.METRIC)

    one_hot_encoder = OneHotEncoder(handle_unknown="ignore")
    one_hot_encoder_bivalue = OneHotEncoder(handle_unknown="ignore", drop='if_binary')
    imputer_metric = SimpleImputer(strategy="mean")

    # create a pipeline to first impute, then scale our metric features
    metric_pipeline = Pipeline(
        steps=[
            ("imputer", imputer_metric),
            ("scaler", StandardScaler()),
            ])

    # encode / scale / impute
    preprocessor = ColumnTransformer(
        sparse_threshold=0,  # generate np array, not sparse matrix
        remainder='drop',
        transformers=[
            ('impute_and_scale_metric', metric_pipeline, metric_features),
            ('one_hot', one_hot_encoder, nominal_features),
            ('one_hot_bivalue', one_hot_encoder_bivalue, nominal_bivalue_features),
            ('passthrough', 'passthrough', boolean_features),
        ],
    )

    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('estimator', model),
    ])

    return pipeline


def _read_db_and_join() -> pd.DataFrame:
    # read from db into dataframe  # noqa
    # i feel more comfortable with joining dataframes than with sqlalchemy...
    engine = create_db_engine(local_config.connection_string)
    df_pollination = (pd.read_sql_query(sql=sqlalchemy.select(Pollination)
                                        .filter(~Pollination.ongoing,
                                                Pollination.pollination_status != 'self_pollinated')  # noqa
                                        , con=engine))
    df_florescence = pd.read_sql_query(sql=sqlalchemy.select(Florescence), con=engine)
    df_plant = pd.read_sql_query(sql=sqlalchemy.select(Plant), con=engine)
    df_taxon = pd.read_sql_query(sql=sqlalchemy.select(Taxon), con=engine)

    # merge with florescences
    df_merged = df_pollination.merge(df_florescence[['id', 'branches_count', 'flowers_count', 'avg_ripening_time']],
                                     how='left',
                                     left_on=['florescence_id'],
                                     right_on=['id'],
                                     validate='many_to_one'  # raise if not unique on right side
                                     )

    # merge with plants for seed capsule
    df_merged2 = df_merged.merge(df_plant[['id', 'taxon_id']],
                                 how='left',
                                 left_on=['seed_capsule_plant_id'],
                                 right_on=['id'],
                                 suffixes=(None, '_seed_capsule'),
                                 validate='many_to_one')  # raise if not unique on right side
    df_merged2.rename({'taxon_id': 'taxon_id_seed_capsule'}, axis=1, inplace=True)

    # merge with plants for pollen donor
    df_merged3 = df_merged2.merge(df_plant[['id', 'taxon_id']],
                                  how='left',
                                  left_on=['pollen_donor_plant_id'],
                                  right_on=['id'],
                                  suffixes=(None, '_pollen_donor'),
                                  validate='many_to_one')  # raise if not unique on right side
    df_merged3.rename({'taxon_id': 'taxon_id_pollen_donor'}, axis=1, inplace=True)

    # merge with taxon for seed capsule
    df_merged4 = df_merged3.merge(df_taxon[['id', 'genus', 'species', 'hybrid', 'hybridgenus']],
                                  how='left',
                                  left_on=['taxon_id_seed_capsule'],
                                  right_on=['id'],
                                  suffixes=(None, '_seed_capsule'),
                                  validate='many_to_one')  # raise if not unique on right side
    df_merged4.rename({'genus': 'genus_seed_capsule',
                       'species': 'species_seed_capsule',
                       'hybrid': 'hybrid_seed_capsule',
                       'hybridgenus': 'hybridgenus_seed_capsule'}, axis=1, inplace=True)

    # merge with taxon for pollen donor
    df = df_merged4.merge(df_taxon[['id', 'genus', 'species', 'hybrid', 'hybridgenus']],
                          how='left',
                          left_on=['taxon_id_pollen_donor'],
                          right_on=['id'],
                          suffixes=(None, '_pollen_donor'),
                          validate='many_to_one')  # raise if not unique on right side
    df.rename({'genus': 'genus_pollen_donor',
               'species': 'species_pollen_donor',
               'hybrid': 'hybrid_pollen_donor',
               'hybridgenus': 'hybridgenus_pollen_donor'}, axis=1, inplace=True)

    return df


def _create_features() -> FeatureContainer:
    """create a features container for a specific model to be trained"""
    features = [
        Feature(column='pollen_type', scale=Scale.NOMINAL_BIVALUE),
        Feature(column='species_seed_capsule', scale=Scale.NOMINAL),
        Feature(column='species_pollen_donor', scale=Scale.NOMINAL),
        Feature(column='genus_seed_capsule', scale=Scale.NOMINAL),
        Feature(column='genus_pollen_donor', scale=Scale.NOMINAL),
        Feature(column='same_genus', scale=Scale.BOOLEAN),
        # Feature(column='seed_capsule_length', scale=Scale.METRIC),
        # Feature(column='seed_capsule_width', scale=Scale.METRIC),
        # Feature(column='seed_length', scale=Scale.METRIC),
        # Feature(column='seed_width', scale=Scale.METRIC),
        # Feature(column='seed_count', scale=Scale.METRIC),
        # Feature(column='avg_ripening_time', scale=Scale.METRIC),
    ]
    # todo: pollination_timestamp (morning, evening, etc.) once enough data is available
    feature_container = FeatureContainer(features=features)
    return feature_container


def _create_data(feature_container: FeatureContainer) -> pd.DataFrame:
    df = _read_db_and_join()

    # add some custom features
    df['same_genus'] = df['genus_pollen_donor'] == df['genus_seed_capsule']
    df['same_species'] = df['species_pollen_donor'] == df['species_seed_capsule']

    if missing := [f for f in feature_container.get_columns() if f not in df.columns]:
        raise ValueError(f'Feature(s) not in dataframe: {missing}')

    return df


def _cv_classifier(x, y, pipeline: Pipeline) -> dict:
    n_groups = 3  # test part will be 1/n
    n_splits = 3  # k-fold will score n times; must be <= n_groups
    np.random.seed(42)
    kfold_groups = np.random.randint(n_groups, size=len(x))
    group_kfold = GroupKFold(n_splits=n_splits)
    with ignore_warnings(category=(ConvergenceWarning, UserWarning)):
        scores = cross_val_score(pipeline, x, y, cv=group_kfold, groups=kfold_groups, scoring='f1')
    print(f'Scores: {scores}')
    print(f'Mean score: {np.mean(scores)}')
    return {'mean_f1_score': np.mean(scores)}


def train_model_for_probability_of_seed_production(db: Session) -> dict:
    """predict whether a pollination attempt is goint to reach SEED status"""
    feature_container = _create_features()
    df = _create_data(feature_container=feature_container)
    # make sure we have only the labels we want (not each must be existent, though)
    assert not set(df.pollination_status.unique()) - {'seed_capsule', 'germinated', 'seed', 'attempt'}
    y = df['pollination_status'].apply(lambda s: 1 if s in {'seed_capsule', 'seed', 'germinated'} else 0)
    x = df[feature_container.get_columns()]

    # train directly on full dataset with optimized hyperparams
    params_knn = {'algorithm': 'ball_tree',
                  'leaf_size': 20,
                  'n_neighbors': 10,
                  'p': 2,
                  'weights': 'distance'}
    model = neighbors.KNeighborsClassifier(**params_knn)
    pipeline = _create_pipeline(feature_container=feature_container, model=model)

    # show f1 cv score
    cv_scores = _cv_classifier(x, y, pipeline)

    # fit with full dataset
    pipeline.fit(x, y)
    pickle_pipeline(pipeline=pipeline, feature_container=feature_container)
    results = cv_scores
    results['model'] = str(model)
    return results
