from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from plants.modules.pollination.enums import PollenType, PredictionModel
from plants.modules.pollination.prediction.ml_common import unpickle_pipeline

if TYPE_CHECKING:
    from sklearn.pipeline import Pipeline

    from plants.modules.plant.models import Plant
    from plants.modules.pollination.models import Florescence
    from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
        FeatureContainer,
    )

pollination_pipeline, feature_container = None, None


def get_probability_of_seed_production_model() -> tuple[Pipeline, FeatureContainer]:
    global pollination_pipeline  # pylint: disable=global-statement
    global feature_container  # pylint: disable=global-statement
    if pollination_pipeline is None:
        pollination_pipeline, feature_container = unpickle_pipeline(
            prediction_model=PredictionModel.POLLINATION_PROBABILITY
        )
    return pollination_pipeline, feature_container


@dataclass
class FeaturesPollination:  # pylint: disable=too-many-instance-attributes
    # location: str
    genus_seed_capsule: str | None
    species_seed_capsule: str | None
    genus_pollen_donor: str | None
    species_pollen_donor: str | None
    pollen_type: str

    hybrid_seed_capsule: bool
    hybridgenus_seed_capsule: bool
    hybrid_pollen_donor: bool
    hybridgenus_pollen_donor: bool
    same_genus: bool
    same_species: bool
    same_plant: bool


def get_data(
    florescence: Florescence,
    pollen_donor: Plant,
    pollen_type: PollenType,
    feature_container_: FeatureContainer,
) -> pd.DataFrame:
    if not florescence.plant.taxon or not pollen_donor.taxon:
        raise ValueError("Plant must have a taxon")

    training_data = FeaturesPollination(
        # location=poll.location,
        genus_seed_capsule=florescence.plant.taxon.genus,
        species_seed_capsule=florescence.plant.taxon.species,
        genus_pollen_donor=pollen_donor.taxon.genus,
        species_pollen_donor=pollen_donor.taxon.species,
        pollen_type=pollen_type.value,
        hybrid_seed_capsule=florescence.plant.taxon.hybrid,
        hybrid_pollen_donor=pollen_donor.taxon.hybrid,
        hybridgenus_seed_capsule=florescence.plant.taxon.hybridgenus,
        hybridgenus_pollen_donor=pollen_donor.taxon.hybridgenus,
        same_genus=florescence.plant.taxon.genus == pollen_donor.taxon.genus,
        same_species=florescence.plant.taxon.species == pollen_donor.taxon.species,
        same_plant=florescence.plant.id == pollen_donor.id,
    )
    df_all = pd.Series(training_data.__dict__).to_frame().T

    if missing := [f for f in feature_container_.get_columns() if f not in df_all.columns]:
        raise ValueError(f"Feature(s) not in dataframe: {missing}")
    return df_all


def predict_probability_of_seed_production(
    florescence: Florescence, pollen_donor: Plant, pollen_type: PollenType
) -> int:
    model, feature_container_ = get_probability_of_seed_production_model()
    df_all = get_data(
        florescence=florescence,
        pollen_donor=pollen_donor,
        pollen_type=pollen_type,
        feature_container_=feature_container_,
    )
    pred_proba = model.predict_proba(df_all)  # e.g. [[0.09839491 0.90160509]]
    probability = pred_proba[0][1]
    return int(probability * 100)
