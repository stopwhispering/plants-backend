from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from plants.modules.pollination.enums import PredictionModel
from plants.modules.pollination.prediction.ml_common import unpickle_pipeline

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sklearn.ensemble import VotingClassifier, VotingRegressor

    from plants.modules.pollination.models import Pollination, SeedPlanting
    from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
        FeatureContainer,
    )

logger = logging.getLogger(__name__)

germination_probability_model, germination_feature_container = None, None
germination_days_model, germination_days_container = None, None


def predict_germination_probability(seed_planting: SeedPlanting) -> int:
    ensemble: VotingClassifier
    ensemble, feature_container = get_germination_probability_model()
    df_all = get_feature_data(
        # seed_planting=seed_planting,
        pollination=seed_planting.pollination,
        feature_container=feature_container,
    )
    proba: list[list[float]] = ensemble.predict_proba(df_all)  # e.g. [[0.09839491 0.90160509]]
    return round(proba[0][1] * 100)


def predict_germination_days(seed_planting: SeedPlanting) -> int:
    ensemble: VotingRegressor
    ensemble, feature_container = get_germination_days_model()
    df_all = get_feature_data(
        # seed_planting=seed_planting,
        pollination=seed_planting.pollination,
        feature_container=feature_container,
    )
    pred: Sequence[float] = ensemble.predict(df_all)  # e.g. array([13.9683266])
    return round(pred[0])


def get_germination_probability_model() -> tuple[VotingClassifier, FeatureContainer]:
    # todo common registry and getter for all models
    global germination_probability_model  # pylint: disable=global-statement
    global germination_feature_container  # pylint: disable=global-statement
    if germination_probability_model is None:
        germination_probability_model, germination_feature_container = unpickle_pipeline(
            prediction_model=PredictionModel.GERMINATION_PROBABILITY
        )
    return germination_probability_model, germination_feature_container


def get_germination_days_model() -> tuple[VotingRegressor, FeatureContainer]:
    # todo common registry and getter for all models
    global germination_days_model  # pylint: disable=global-statement
    global germination_days_container  # pylint: disable=global-statement
    if germination_days_model is None:
        germination_days_model, germination_days_container = unpickle_pipeline(
            prediction_model=PredictionModel.GERMINATION_DAYS
        )
    return germination_days_model, germination_days_container


@dataclass
class FeaturesSeedPlanting:  # pylint: disable=too-many-instance-attributes
    genus_seed_capsule: str | None  # one-hot-encoded to all-zero if None
    species_seed_capsule: str | None
    genus_pollen_donor: str | None
    species_pollen_donor: str | None

    hybrid_seed_capsule: bool
    hybrid_pollen_donor: bool
    hybridgenus_seed_capsule: bool
    hybridgenus_pollen_donor: bool
    same_genus: bool
    same_species: bool

    seed_capsule_length: float | None  # imputed with KNN if None
    seed_length: float | None
    seed_width: float | None


def get_feature_data(
    # seed_planting: SeedPlanting,  # noqa: ARG001
    pollination: Pollination,
    feature_container: FeatureContainer,
) -> pd.DataFrame:
    features = FeaturesSeedPlanting(
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
        seed_capsule_length=float(pollination.seed_capsule_length)
        if pollination.seed_capsule_length
        else None,
        seed_length=float(pollination.seed_length) if pollination.seed_length else None,
        seed_width=float(pollination.seed_width) if pollination.seed_width else None,
    )
    df_all = pd.Series(features.__dict__).to_frame().T

    if missing := [f for f in feature_container.get_columns() if f not in df_all.columns]:
        raise ValueError(f"Feature(s) not in dataframe: {missing}")
    return df_all
