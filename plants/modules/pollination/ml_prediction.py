from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from plants.extensions.ml_models import get_probability_of_seed_production_model

if TYPE_CHECKING:
    from ml_helpers.preprocessing.features import FeatureContainer
    from plants.modules.plant.models import Plant
    from plants.modules.pollination.enums import PollenType
    from plants.modules.pollination.models import Florescence


@dataclass
class TrainingData:
    pollen_type: str
    flowers_count: int | None
    branches_count: int | None
    genus_seed_capsule: str
    genus_pollen_donor: str
    species_seed_capsule: str | None
    species_pollen_donor: str | None
    hybrid_seed_capsule: bool
    hybrid_pollen_donor: bool
    hybridgenus_seed_capsule: bool
    hybridgenus_pollen_donor: bool
    same_genus: bool
    same_species: bool


def get_data(
    florescence: Florescence,
    pollen_donor: Plant,
    pollen_type: PollenType,
    feature_container: FeatureContainer,
) -> pd.DataFrame:
    if not florescence.plant.taxon or not pollen_donor.taxon:
        raise ValueError("Plant must have a taxon")

    traing_data = TrainingData(
        pollen_type=pollen_type.value,
        flowers_count=florescence.flowers_count,
        branches_count=florescence.branches_count,
        genus_seed_capsule=florescence.plant.taxon.genus,
        genus_pollen_donor=pollen_donor.taxon.genus,
        species_seed_capsule=florescence.plant.taxon.species,
        species_pollen_donor=pollen_donor.taxon.species,
        hybrid_seed_capsule=florescence.plant.taxon.hybrid,
        hybrid_pollen_donor=pollen_donor.taxon.hybrid,
        hybridgenus_seed_capsule=florescence.plant.taxon.hybridgenus,
        hybridgenus_pollen_donor=pollen_donor.taxon.hybridgenus,
        same_genus=florescence.plant.taxon.genus == pollen_donor.taxon.genus,
        same_species=florescence.plant.taxon.species == pollen_donor.taxon.species,
    )
    df_all = pd.Series(traing_data.__dict__).to_frame().T

    if missing := [
        f for f in feature_container.get_columns() if f not in df_all.columns
    ]:
        raise ValueError(f"Feature(s) not in dataframe: {missing}")
    return df_all


def predict_probability_of_seed_production(
    florescence: Florescence, pollen_donor: Plant, pollen_type: PollenType
) -> int:
    pipeline, feature_container = get_probability_of_seed_production_model()
    df_all = get_data(
        florescence=florescence,
        pollen_donor=pollen_donor,
        pollen_type=pollen_type,
        feature_container=feature_container,
    )
    pred_proba = pipeline.predict_proba(df_all)  # e.g. [[0.09839491 0.90160509]]
    probability = pred_proba[0][1]
    return int(probability * 100)
