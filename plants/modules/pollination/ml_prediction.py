import pandas as pd

from ml_helpers.preprocessing.features import FeatureContainer
from plants.extensions.ml_models import get_probability_of_seed_production_model
from plants.modules.plant.models import Plant
from plants.modules.pollination.models import Florescence, PollenType


def get_data(florescence: Florescence,
             pollen_donor: Plant,
             pollen_type: PollenType,
             feature_container: FeatureContainer) -> pd.DataFrame:
    data = {'pollen_type': pollen_type.value,
            'flowers_count': florescence.flowers_count,
            'branches_count': florescence.branches_count,
            'genus_seed_capsule': florescence.plant.taxon.genus,
            'genus_pollen_donor': pollen_donor.taxon.genus,
            'species_seed_capsule': florescence.plant.taxon.species,
            'species_pollen_donor': pollen_donor.taxon.species,
            'hybrid_seed_capsule': florescence.plant.taxon.hybrid,
            'hybrid_pollen_donor': pollen_donor.taxon.hybrid,
            'hybridgenus_seed_capsule': florescence.plant.taxon.hybridgenus,
            'hybridgenus_pollen_donor': pollen_donor.taxon.hybridgenus, }
    df = pd.Series(data).to_frame().T

    df['same_genus'] = df['genus_pollen_donor'] == df['genus_seed_capsule']
    df['same_species'] = df['species_pollen_donor'] == df['species_seed_capsule']

    if missing := [f for f in feature_container.get_columns() if f not in df.columns]:
        raise ValueError(f'Feature(s) not in dataframe: {missing}')
    return df


def predict_probability_of_seed_production(florescence: Florescence,
                                           pollen_donor: Plant,
                                           pollen_type: PollenType) -> int:
    pipeline, feature_container = get_probability_of_seed_production_model()
    df = get_data(florescence=florescence,
                  pollen_donor=pollen_donor,
                  pollen_type=pollen_type,
                  feature_container=feature_container)
    pred_proba = pipeline.predict_proba(df)  # e.g. [[0.09839491 0.90160509]]
    probability = pred_proba[0][1]
    return int(probability*100)
