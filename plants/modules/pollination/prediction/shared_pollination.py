from __future__ import annotations

import logging
import pandas as pd


logger = logging.getLogger(__name__)


CATEGORICAL_FEATURES = [
    # "location",
    "genus_seed_capsule",
    "species_seed_capsule",
    "genus_pollen_donor",
    "species_pollen_donor",
    "pollen_type",
    "pollen_quality",
    "seed_capsule_plant_id_as_cat",
    "pollen_donor_plant_id_as_cat",
]

BOOLEAN_FEATURES = [
    "hybrid_seed_capsule",
    "hybridgenus_seed_capsule",
    "hybrid_pollen_donor",
    "hybridgenus_pollen_donor",
    "same_genus",
    "same_species",
    "same_plant",
]

NUMERIC_FEATURES = [
    "pollinated_at_hour_sin",
    "pollinated_at_hour_cos",
    "count_attempted",
]


def validate_and_set_dtypes(df: pd.DataFrame):
    # dropped = [
    #     c for c in df.columns if c not in CATEGORICAL_FEATURES + BOOLEAN_FEATURES + NUMERIC_FEATURES
    # ]
    # logger.info(f"Columns not used for prediction:\n{dropped}")

    missing = [
        c for c in CATEGORICAL_FEATURES + BOOLEAN_FEATURES + NUMERIC_FEATURES if c not in df.columns
    ]
    if missing:
        raise ValueError(f"Missing:\n{missing}")

    for col in CATEGORICAL_FEATURES:
        df[col] = df[col].astype("str").astype("category")
    for col in BOOLEAN_FEATURES:
        assert df[col].dtype == "bool", f"{col} is not bool"
    for col in NUMERIC_FEATURES:
        assert df[col].dtype in ("float64", "int64"), f"{col} is not numeric"

    return df[CATEGORICAL_FEATURES + BOOLEAN_FEATURES + NUMERIC_FEATURES]
