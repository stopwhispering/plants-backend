from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import TYPE_CHECKING

import pandas as pd
from xgboost import XGBClassifier
import numpy as np
from plants.modules.event.models import Event
from plants.modules.pollination.enums import PollenType, PredictionModel
from plants.modules.pollination.prediction.ml_common import unpickle_pipeline
from plants.modules.pollination.prediction.train_florescence import add_potting_info_to_train

if TYPE_CHECKING:
    from sklearn.pipeline import Pipeline

    from plants.modules.plant.models import Plant
    from plants.modules.pollination.models import Florescence
    from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
        FeatureContainer,
    )
import pandas as pd
florescence_model = None
category_map = None


def get_probability_of_florescence_model() -> tuple[XGBClassifier, dict]:
    global florescence_model  # pylint: disable=global-statement
    global category_map
    if florescence_model is None:
        florescence_model, _, category_map = unpickle_pipeline(
            prediction_model=PredictionModel.FLORESCENCE_PROBABILITY,
            return_category_map=True,
        )
    return florescence_model, category_map


def add_potting_info_for_pred(df: pd.DataFrame, plant: Plant) -> pd.DataFrame:
    """Find latest pot diameter and assign it to each month;
    cf. add_potting_info_to_train for training"""
    # find the latest event in plant.events that has a pot
    latest_event = None
    for event in plant.events:
        if event.pot and event.pot.diameter_width:
            if latest_event is None or event.date > latest_event.date:
                latest_event = event
    if latest_event:
        df["pot_diameter"] = latest_event.pot.diameter_width
    else:
        df["pot_diameter"] = None
    df["pot_diameter"] = df["pot_diameter"].astype(float)
    return df


def add_features_for_pred(df: pd.DataFrame, plant: Plant) -> pd.DataFrame:
    """cf. add_features_to_train for training"""
    # extract calendar month and sine/cosine features
    df["month"] = df["year_month"].dt.month
    df["month_sin"] = np.sin(2 * np.pi * (df["month"] - 1) / 12)
    df["month_cos"] = np.cos(2 * np.pi * (df["month"] - 1) / 12)

    df['species'] = plant.taxon.species if plant.taxon else None
    df['genus'] = plant.taxon.genus if plant.taxon else None
    df['is_custom'] = plant.taxon.is_custom if plant.taxon else False
    df['plant_name'] = plant.plant_name

    # if "cv" in plant_name, make is_custom True
    ser_is_cv = df["plant_name"].apply(lambda x: "cv" in x.lower())
    df["is_custom"] = (df["is_custom"] == True) | ser_is_cv  # noqa

    # # make nan and None the same
    # df_train = df_train.fillna("None")

    # # remove all 2024
    # df_train = df_train[df_train["year_month"].dt.year != 2024]
    # df_train = df_train.reset_index(drop=True)
    #
    # df_train = df_train.drop(
    #     columns=["year_month", "id", "plant_name"]
    # )  # id is a duplicate of plant_id

    # plant id should be considered a category, not a number
    df["plant_id"] = df["plant_id"].astype("category")
    df["species"] = df["species"].astype("category")
    df["genus"] = df["genus"].astype("category")

    # plant_name is superfluous since we have plant_id as category
    df = df.drop(columns=["plant_name"])

    return df


def _load_florescence_model_and_predict(df: pd.DataFrame):
    """
    Expected features:
        'plant_id': category
        'pot_diameter': float64
        'month': int32
        'month_sin': float64
        'month_cos': float64
        'species': category
        'genus': category
        'is_custom': bool
    cf. train_and_pickle_xgb_florescence_model for prediction
    """
    model, category_map = get_probability_of_florescence_model()

    # for xgb with native categories, we need to align the categories to the training data
    for col in df.select_dtypes('category').columns:
        df[col] = pd.Categorical(df[col], categories=category_map[col])

    pred_proba = model.predict_proba(df.drop(columns=["year_month"]))  # e.g. [[0.09839491 0.90160509]]
    probability_for_florescence = pred_proba[:, 1]

    df_pred = df.copy()
    df_pred["pred"] = probability_for_florescence

    # df.drop(columns=["year_month"]).to_pickle("/common/delme.pkl")

    return df_pred


def predict_probability_of_florescence(
    plant: Plant,
) -> list[tuple[int, int, float]]:

    # get remaining months of current year, starting from following month
    current_year = datetime.today().year
    first_month = datetime.today().month + 1  # todo handle December case
    remaining_months = [
        datetime(current_year, month, 1).date() for month in range(first_month, 13)
    ]

    # get all months of next year
    next_year = current_year + 1
    next_year_months = [
        datetime(next_year, month, 1).date() for month in range(1, 13)
    ]
    months = remaining_months + next_year_months

    # we need a train-like dataframe with one row per month
    df = pd.DataFrame(
        {
            "plant_id": [plant.id] * len(months),
            "year_month": months,
        }
    )
    df['year_month'] = pd.to_datetime(df['year_month'])

    df = add_potting_info_for_pred(df, plant)
    df = add_features_for_pred(df, plant)

    df_preds = _load_florescence_model_and_predict(df)

    results = []
    for index, row in df_preds.iterrows():
        year = row["year_month"].year
        month = row["year_month"].month
        probability = row["pred"]
        results.append((year, month, probability))

    return results
