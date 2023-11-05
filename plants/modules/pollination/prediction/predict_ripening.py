from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from plants.modules.pollination.enums import PredictionModel
from plants.modules.pollination.prediction.ml_common import unpickle_pipeline

if TYPE_CHECKING:
    from sklearn.ensemble import VotingRegressor

    from plants.modules.pollination.models import Pollination
    from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
        FeatureContainer,
    )

logger = logging.getLogger(__name__)

ripening_days_regressor, feature_container = None, None


def predict_ripening_days(pollination: Pollination) -> int:
    ensemble, feature_container = get_ripening_days_model()
    df_all = get_feature_data(
        pollination=pollination,
        feature_container=feature_container,
    )
    pred = ensemble.predict(df_all)  # e.g. [[0.09839491 0.90160509]]
    return round(pred[0])


def get_ripening_days_model() -> tuple[VotingRegressor, FeatureContainer]:
    global ripening_days_regressor
    global feature_container
    if ripening_days_regressor is None:
        ripening_days_regressor, feature_container = unpickle_pipeline(
            prediction_model=PredictionModel.RIPENING_DAYS
        )
    return ripening_days_regressor, feature_container


@dataclass
class FeaturesRipeningDays:  # pylint: disable=too-many-instance-attributes
    location: str
    genus_seed_capsule: str | None
    species_seed_capsule: str | None
    genus_pollen_donor: str | None
    species_pollen_donor: str | None

    hybrid_seed_capsule: bool
    hybrid_pollen_donor: bool
    hybridgenus_seed_capsule: bool
    hybridgenus_pollen_donor: bool
    same_genus: bool
    same_species: bool


def get_feature_data(pollination: Pollination, feature_container: FeatureContainer) -> pd.DataFrame:
    features = FeaturesRipeningDays(
        location=pollination.location,
        genus_seed_capsule=pollination.seed_capsule_plant.taxon.genus
        if pollination.seed_capsule_plant.taxon and pollination.seed_capsule_plant.taxon.genus
        else None,
        species_seed_capsule=pollination.seed_capsule_plant.taxon.species
        if pollination.seed_capsule_plant.taxon and pollination.seed_capsule_plant.taxon.species
        else None,
        genus_pollen_donor=pollination.pollen_donor_plant.taxon.genus
        if pollination.pollen_donor_plant.taxon and pollination.pollen_donor_plant.taxon.genus
        else None,
        species_pollen_donor=pollination.pollen_donor_plant.taxon.species
        if pollination.pollen_donor_plant.taxon and pollination.pollen_donor_plant.taxon.species
        else None,
        hybrid_seed_capsule=pollination.seed_capsule_plant.taxon.hybrid
        if pollination.seed_capsule_plant.taxon
        else False,
        hybrid_pollen_donor=pollination.pollen_donor_plant.taxon.hybrid
        if pollination.pollen_donor_plant.taxon
        else False,
        hybridgenus_seed_capsule=pollination.seed_capsule_plant.taxon.hybridgenus
        if pollination.seed_capsule_plant.taxon
        else False,
        hybridgenus_pollen_donor=pollination.pollen_donor_plant.taxon.hybridgenus
        if pollination.pollen_donor_plant.taxon
        else False,
        same_genus=(
            pollination.seed_capsule_plant.taxon.genus == pollination.pollen_donor_plant.taxon.genus
        )
        if pollination.seed_capsule_plant.taxon and pollination.pollen_donor_plant.taxon
        else False,
        same_species=(
            pollination.seed_capsule_plant.taxon.species
            == pollination.pollen_donor_plant.taxon.species
        )
        if pollination.seed_capsule_plant.taxon and pollination.pollen_donor_plant.taxon
        else False,
    )
    df_all = pd.Series(features.__dict__).to_frame().T

    if missing := [f for f in feature_container.get_columns() if f not in df_all.columns]:
        raise ValueError(f"Feature(s) not in dataframe: {missing}")
    return df_all
