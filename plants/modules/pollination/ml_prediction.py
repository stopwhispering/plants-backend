from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from plants.extensions.ml_models import get_probability_of_seed_production_model

if TYPE_CHECKING:
    from ml_helpers.preprocessing.features import FeatureContainer
    from plants.modules.plant.models import Plant
    from plants.modules.pollination.enums import PollenType
    from plants.modules.pollination.models import Florescence


def get_data(
    florescence: Florescence,
    pollen_donor: Plant,
    pollen_type: PollenType,
    feature_container: FeatureContainer,
) -> pd.DataFrame:
    data = {  # todo type-check with dataclass or pydantic or similar
        "pollen_type": pollen_type.value,
        "flowers_count": florescence.flowers_count,
        "branches_count": florescence.branches_count,
        "genus_seed_capsule": florescence.plant.taxon.genus,
        "genus_pollen_donor": pollen_donor.taxon.genus,
        "species_seed_capsule": florescence.plant.taxon.species,
        "species_pollen_donor": pollen_donor.taxon.species,
        "hybrid_seed_capsule": florescence.plant.taxon.hybrid,
        "hybrid_pollen_donor": pollen_donor.taxon.hybrid,
        "hybridgenus_seed_capsule": florescence.plant.taxon.hybridgenus,
        "hybridgenus_pollen_donor": pollen_donor.taxon.hybridgenus,
    }
    df_all = pd.Series(data).to_frame().T

    df_all["same_genus"] = df_all["genus_pollen_donor"] == df_all["genus_seed_capsule"]
    df_all["same_species"] = (
        df_all["species_pollen_donor"] == df_all["species_seed_capsule"]
    )

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
