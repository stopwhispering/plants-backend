from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

from plants.modules.pollination.enums import PollenQuality, PollenType, PredictionModel
from plants.modules.pollination.prediction.ml_common import unpickle_pipeline
from plants.modules.pollination.prediction.shared_pollination import validate_and_set_dtypes

if TYPE_CHECKING:
    from sklearn.pipeline import Pipeline

    from plants.modules.plant.models import Plant
    from plants.modules.pollination.models import Florescence

pollination_pipeline, feature_container = None, None


def get_probability_of_seed_production_model() -> Pipeline | LGBMClassifier:
    global pollination_pipeline  # pylint: disable=global-statement
    global feature_container  # pylint: disable=global-statement
    if pollination_pipeline is None:
        pollination_pipeline, _ = unpickle_pipeline(
            prediction_model=PredictionModel.POLLINATION_PROBABILITY
        )
    return pollination_pipeline


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

    pollen_quality: PollenQuality | None
    pollinated_at_hour_sin: float | None
    pollinated_at_hour_cos: float | None
    seed_capsule_plant_id_as_cat: any  # Category
    pollen_donor_plant_id_as_cat: any  # Category
    count_attempted: int | None


def get_data(
    florescence: Florescence,
    pollen_donor: Plant,
    pollen_type: PollenType,
    pollen_quality: PollenQuality,
    count_attempted: int,
    pollinated_at_datetime_utc: datetime.datetime,
) -> pd.DataFrame:
    if not florescence.plant.taxon or not pollen_donor.taxon:
        raise ValueError("Plant must have a taxon")

    # see make_preprocessor() in train_pollination.py for the features used in training
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
        pollen_quality=pollen_quality,
        pollinated_at_hour_sin=np.sin(2 * np.pi * pollinated_at_datetime_utc.hour / 24),
        pollinated_at_hour_cos=np.cos(2 * np.pi * pollinated_at_datetime_utc.hour / 24),
        seed_capsule_plant_id_as_cat=str(florescence.plant.id),  # will be converted to category later
        pollen_donor_plant_id_as_cat=str(pollen_donor.id),  # will be converted to category later
        count_attempted=count_attempted,
    )
    # df_all = pd.Series(training_data.__dict__).to_frame().T
    df_all = pd.DataFrame([training_data.__dict__])
    return df_all


def predict_probability_lgbm(clf: LGBMClassifier, df_all: pd.DataFrame) -> float:
    """
    Notes:
    * data must match df_train_processed in train_probability_model_lgbm() in train_pollination.py
    """
    df_processed = validate_and_set_dtypes(df_all)
    arr_pred_proba = clf.predict_proba(df_processed)  # e.g. [[0.09839491 0.90160509]]
    probability = arr_pred_proba[0][1]
    return probability


def predict_probability_of_seed_production(
    florescence: Florescence, pollen_donor: Plant, pollen_type: PollenType,
    count_attempted: int, pollen_quality: PollenQuality,
    pollinated_at_datetime_utc: datetime.datetime,
) -> int:
    model = get_probability_of_seed_production_model()
    df_all = get_data(
        florescence=florescence,
        pollen_donor=pollen_donor,
        pollen_type=pollen_type,
        pollen_quality=pollen_quality,
        count_attempted=count_attempted,
        pollinated_at_datetime_utc=pollinated_at_datetime_utc,
    )
    if type(model) is LGBMClassifier:
        probability = predict_probability_lgbm(model, df_all)
        return int(probability * 100)

    # todo remove rest if no longer needed
    pred_proba = model.predict_proba(df_all)  # e.g. [[0.09839491 0.90160509]]
    probability = pred_proba[0][1]
    return int(probability * 100)
