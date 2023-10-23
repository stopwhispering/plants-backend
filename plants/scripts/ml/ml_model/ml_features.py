from enum import Enum

from plants.modules.pollination.ml_helpers.preprocessing.features import (
    Feature,
    FeatureContainer,
    Scale,
)


class ModelType(Enum):
    POLLINATION_TO_SEED = 1
    POLLINATION_TO_GERMINATION = 2


def create_features(model_type: ModelType) -> FeatureContainer:
    """Create a features container for a specific model to be trained."""
    # plant and flower features all models
    features = [
        Feature(column="pollen_type", scale=Scale.NOMINAL_BIVALUE),
        # Feature(column='flowers_count', scale=Scale.METRIC),  # activate some
        # features once we have more data
        # Feature(column='branches_count', scale=Scale.METRIC),
        Feature(column="species_seed_capsule", scale=Scale.NOMINAL),
        Feature(column="species_pollen_donor", scale=Scale.NOMINAL),
        Feature(column="genus_seed_capsule", scale=Scale.NOMINAL),
        Feature(column="genus_pollen_donor", scale=Scale.NOMINAL),
        # Feature(column='hybrid_seed_capsule', scale=Scale.NOMINAL_BIVALUE),
        # Feature(column='hybrid_pollen_donor', scale=Scale.NOMINAL_BIVALUE),
        # Feature(column='hybridgenus_seed_capsule', scale=Scale.NOMINAL_BIVALUE),
        # Feature(column='hybridgenus_pollen_donor', scale=Scale.NOMINAL_BIVALUE),
        Feature(column="same_genus", scale=Scale.BOOLEAN),
        # Feature(column='same_species', scale=Scale.BOOLEAN),
    ]

    # todo: pollination_timestamp (morning, evening, etc.) once enough data is available

    # for the label predicting whether a seed is going to be germinated, we have seed
    # attributes to be considered
    if model_type == ModelType.POLLINATION_TO_GERMINATION:
        features.extend(
            [
                Feature(column="seed_capsule_length", scale=Scale.METRIC),
                Feature(column="seed_capsule_width", scale=Scale.METRIC),
                Feature(column="seed_length", scale=Scale.METRIC),
                Feature(column="seed_width", scale=Scale.METRIC),
                Feature(column="seed_count", scale=Scale.METRIC),
                Feature(column="avg_ripening_time", scale=Scale.METRIC),
                # todo harvest_date quarter
                # todo days_between_harvest_and_sowing
            ]
        )

    feature_container = FeatureContainer(features=features)
    return feature_container
