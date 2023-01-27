import sqlalchemy
import pandas as pd

from ml_helpers.preprocessing.features import FeatureContainer
from plants import local_config
from plants.modules.plant.models import Plant
from plants.dependencies import get_db
from plants.extensions.db import create_db_engine
from plants.extensions.orm import init_orm
from plants.modules.pollination.models import Pollination, Florescence
from plants.modules.taxon.models import Taxon

init_orm(engine=create_db_engine(local_config.connection_string))
db = next(get_db())


def _read_db_and_join() -> pd.DataFrame:
    # read from db into dataframe
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


def create_data(feature_container: FeatureContainer) -> pd.DataFrame:
    df = _read_db_and_join()

    # add some custom features
    df['same_genus'] = df['genus_pollen_donor'] == df['genus_seed_capsule']
    df['same_species'] = df['species_pollen_donor'] == df['species_seed_capsule']

    if missing := [f for f in feature_container.get_columns() if f not in df.columns]:
        raise ValueError(f'Feature(s) not in dataframe: {missing}')

    return df
