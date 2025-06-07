from __future__ import annotations

import asyncio
import calendar
from collections import defaultdict
from datetime import date, datetime

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold
from xgboost import XGBClassifier

from plants.modules.pollination.prediction.florescence_data import assemble_florescence_data


def get_created_at_date(ser_plant: pd.Series) -> date | None:
    if ser_plant["created_at"].year != 1900:
        return datetime.date(ser_plant["created_at"])
    return None


def get_last_updated_at(ser_plant: pd.Series) -> date | None:
    if not pd.isna(ser_plant["last_updated_at"]):
        return datetime.date(ser_plant["last_updated_at"])
    return None


def get_first_last_florescence_creation_date(
    ser_plant: pd.Series,
    first: bool,
    df_florescence: pd.DataFrame,
) -> date | None:
    df_florescence_plant = df_florescence[
        (df_florescence["plant_id"] == ser_plant["id"])
        & (df_florescence["created_at"].dt.year != 1900)
        & ~df_florescence["created_at"].isna()
    ]
    if df_florescence_plant.empty:
        return None
    if first:
        return datetime.date(df_florescence_plant["created_at"].min())
    return datetime.date(df_florescence_plant["created_at"].max())


def get_first_last_florescence_flowering_date(
    ser_plant: pd.Series,
    first: bool,
    df_florescence: pd.DataFrame,
) -> date | None:
    df_florescence_plant = df_florescence[
        (df_florescence["plant_id"] == ser_plant["id"])
        # & (df_florescence['first_flower_opened_at'].dt.year != 1900)
        & (~df_florescence["first_flower_opened_at"].isna())
    ]
    if df_florescence_plant.empty:
        return None
    if first:
        return df_florescence_plant["first_flower_opened_at"].min()
    return df_florescence_plant["first_flower_opened_at"].max()


def get_first_last_event_date(
    ser_plant: pd.Series,
    first: bool,
    df_event: pd.DataFrame,
) -> date | None:  # noqa: FBT001
    df_event_plant = df_event[df_event["plant_id"] == ser_plant["id"]]
    # todo: seedling etc...
    if not df_event_plant.empty:
        if first:
            return datetime.strptime(df_event_plant["date"].min(), "%Y-%m-%d").date()  # noqa
        return datetime.strptime(df_event_plant["date"].max(), "%Y-%m-%d").date()  # noqa
    return None


def get_cancellation_date(ser_plant: pd.Series) -> date | None:
    if not pd.isna(ser_plant["cancellation_date"]):
        return ser_plant["cancellation_date"]
    return None


def get_first_last_date_per_plant(
    df_plant: pd.DataFrame,
    df_event: pd.DataFrame,
    df_florescence: pd.DataFrame,
) -> dict[int, tuple[date, date]]:
    # for each plant, we need to approximate the first and last date
    results: dict[int, tuple[date, date]] = {}
    for _, ser_plant in df_plant.iterrows():
        # todo filter plants eg by genus
        if ser_plant["deleted"]:
            continue
        plant_created_at = get_created_at_date(ser_plant)
        plant_last_updated_at = get_last_updated_at(ser_plant)
        first_florescence_created_at = get_first_last_florescence_creation_date(
            ser_plant, first=True, df_florescence=df_florescence
        )
        first_florescence_first_flower_opened_at = get_first_last_florescence_flowering_date(
            ser_plant,
            first=True,
            df_florescence=df_florescence,
        )
        first_event_date = get_first_last_event_date(
            ser_plant,
            first=True,
            df_event=df_event,
        )

        # take the earlisest date
        aquisition_date = min(
            plant_created_at if plant_created_at else pd.Timestamp.max.date(),
            plant_last_updated_at if plant_last_updated_at else pd.Timestamp.max.date(),
            first_florescence_created_at
            if first_florescence_created_at
            else pd.Timestamp.max.date(),
            first_florescence_first_flower_opened_at
            if first_florescence_first_flower_opened_at
            else pd.Timestamp.max.date(),
            first_event_date if first_event_date else pd.Timestamp.max.date(),
        )
        if aquisition_date.year < 2016 or aquisition_date.year > 2028:
            raise ValueError("Unexpected aquisition date: " + str(aquisition_date))

        plant_cancellation_date = get_cancellation_date(ser_plant)
        # plant_last_updated_at = get_last_updated_at(ser_plant)
        last_florescence_created_at = get_first_last_florescence_creation_date(
            ser_plant,
            first=False,
            df_florescence=df_florescence,
        )
        last_florescence_first_flower_opened_at = get_first_last_florescence_flowering_date(
            ser_plant,
            first=False,
            df_florescence=df_florescence,
        )
        last_event_date = get_first_last_event_date(ser_plant, first=False, df_event=df_event)

        if ser_plant["active"]:
            # today
            termination_date = date.today()  # noqa
        elif plant_cancellation_date:
            termination_date = plant_cancellation_date
        else:
            termination_date = max(
                plant_last_updated_at if plant_last_updated_at else pd.Timestamp.min.date(),
                last_florescence_created_at
                if last_florescence_created_at
                else pd.Timestamp.min.date(),
                last_florescence_first_flower_opened_at
                if last_florescence_first_flower_opened_at
                else pd.Timestamp.min.date(),
                last_event_date if last_event_date else pd.Timestamp.min.date(),
            )

        if termination_date.year < 2016 or termination_date.year > 2028:
            raise ValueError("Unexpected termination_date date: " + str(termination_date))

        results[ser_plant["id"]] = aquisition_date, termination_date

    return results


def compute_mean_days_as_filler(
    df_florescence: pd.DataFrame,
):
    # get mean days between first flower and inflorescence appeared
    df_flor_1 = df_florescence[
        (~df_florescence["inflorescence_appeared_at"].isna())
        & (~df_florescence["first_flower_opened_at"].isna())
    ].copy()
    df_flor_1["inflorescence_appeared_at"] = pd.to_datetime(df_flor_1["inflorescence_appeared_at"])
    df_flor_1["first_flower_opened_at"] = pd.to_datetime(df_flor_1["first_flower_opened_at"])
    avg_days_between_appeared_and_opened = (
        df_flor_1["first_flower_opened_at"] - df_flor_1["inflorescence_appeared_at"]
    ).dt.days.median()

    # get the mean days between last flower closed and inflorescence appeared
    df_flor_2 = df_florescence[
        (~df_florescence["inflorescence_appeared_at"].isna())
        & (~df_florescence["last_flower_closed_at"].isna())
    ].copy()
    df_flor_2["inflorescence_appeared_at"] = pd.to_datetime(df_flor_2["inflorescence_appeared_at"])
    df_flor_2["last_flower_closed_at"] = pd.to_datetime(df_flor_2["last_flower_closed_at"])
    avg_days_between_appeared_and_closed = (
        df_flor_2["last_flower_closed_at"] - df_flor_2["inflorescence_appeared_at"]
    ).dt.days.median()

    # get the mean days between first flower opened and last flower closed
    df_flor_3 = df_florescence[
        (~df_florescence["first_flower_opened_at"].isna())
        & (~df_florescence["last_flower_closed_at"].isna())
    ].copy()
    df_flor_3["first_flower_opened_at"] = pd.to_datetime(df_flor_3["first_flower_opened_at"])
    df_flor_3["last_flower_closed_at"] = pd.to_datetime(df_flor_3["last_flower_closed_at"])
    avg_days_between_opened_and_closed = (
        df_flor_3["last_flower_closed_at"] - df_flor_3["first_flower_opened_at"]
    ).dt.days.median()

    return (
        avg_days_between_appeared_and_opened,
        avg_days_between_appeared_and_closed,
        avg_days_between_opened_and_closed,
    )


def flowering_months_per_plant(
    plant_ids: list[int], df_florescence: pd.DataFrame
) -> dict[int, set[date]]:
    """Retrieve the flowering months for each plant."""
    (
        avg_days_between_appeared_and_opened,
        avg_days_between_appeared_and_closed,
        avg_days_between_opened_and_closed,
    ) = compute_mean_days_as_filler(df_florescence)

    results: dict[int, set[date]] = defaultdict(set)
    for _, ser_florescence in df_florescence.iterrows():
        if ser_florescence["plant_id"] not in plant_ids:
            continue

        # in the best case we have an appearance date
        if not pd.isna(ser_florescence["inflorescence_appeared_at"]):
            appearance_date = ser_florescence["inflorescence_appeared_at"]
        elif not pd.isna(ser_florescence["first_flower_opened_at"]):
            appearance_date = ser_florescence["first_flower_opened_at"] - pd.Timedelta(
                days=avg_days_between_appeared_and_opened
            )
        elif not pd.isna(ser_florescence["last_flower_closed_at"]):
            appearance_date = ser_florescence["last_flower_closed_at"] - pd.Timedelta(
                days=avg_days_between_appeared_and_closed
            )
        else:
            continue  # no appearance date available

        # in the best case we have a closed date
        if not pd.isna(ser_florescence["last_flower_closed_at"]):
            closed_date = ser_florescence["last_flower_closed_at"]
        elif not pd.isna(ser_florescence["first_flower_opened_at"]):
            closed_date = ser_florescence["first_flower_opened_at"] + pd.Timedelta(
                days=avg_days_between_opened_and_closed
            )
        elif not pd.isna(ser_florescence["inflorescence_appeared_at"]):
            closed_date = ser_florescence["inflorescence_appeared_at"] + pd.Timedelta(
                days=avg_days_between_appeared_and_closed
            )
        else:
            continue  # no closed date available

        # for the sake of simplicity, we use the first of the month for appearance and closed date
        appearance_month = appearance_date.replace(day=1)
        closed_month = closed_date.replace(day=1)

        # now we collect all months, including inbetween
        months = set()
        current_month = appearance_month
        while current_month <= closed_month:
            months.add(current_month)
            current_month = (current_month + pd.DateOffset(months=1)).replace(day=1).date()

        results[ser_florescence["plant_id"]].update(months)

    return results


def get_plant_to_month_targets(
    plant_id_to_first_last_date: dict, plant_id_to_flowering_months: dict
) -> pd.DataFrame:
    # now we iterate over the plants and months and flag the plant/month combinations with flowering
    results = []
    for plant_id, (first_month, last_month) in plant_id_to_first_last_date.items():
        # print(f"Plant ID: {plant_id}, First Month: {first_month}, Last Month: {last_month}")

        # iterate through the months from first to last
        current_month = first_month
        while current_month <= last_month:
            current_month = current_month.replace(day=1)
            if current_month in plant_id_to_flowering_months.get(plant_id, set()):
                # print(f"  Flowering in month: {current_month}")
                results.append((plant_id, current_month, True))
            else:
                # print(f"  Not flowering in month: {current_month}")
                results.append((plant_id, current_month, False))
            current_month = (current_month + pd.DateOffset(months=1)).replace(day=1).date()

    df_results = pd.DataFrame(results, columns=["plant_id", "year_month", "flowering"])
    # duplicates = df_results[df_results.duplicated(subset=['plant_id', 'month'], keep=False)]
    assert not df_results.duplicated(subset=["plant_id", "year_month"]).any()
    df_results["year_month"] = pd.to_datetime(df_results["year_month"])
    return df_results


def add_features(
    df_train: pd.DataFrame, df_plant: pd.DataFrame
) -> tuple[pd.DataFrame, pd.Series]:
    # extract calendar month and sine/cosine features
    df_train["month"] = df_train["year_month"].dt.month
    df_train["month_sin"] = np.sin(2 * np.pi * (df_train["month"] - 1) / 12)
    df_train["month_cos"] = np.cos(2 * np.pi * (df_train["month"] - 1) / 12)

    # species, genus, is_custom
    # read 'species', 'genus', 'is_custom' from df_plant
    df_train = df_train.merge(
        df_plant[["id", "species", "genus", "is_custom", "plant_name"]],
        how="left",
        left_on="plant_id",
        right_on="id",
        suffixes=("", "_plant"),
    )

    # if "cv" in plant_name, make is_custom True
    ser_is_cv = df_train["plant_name"].apply(lambda x: "cv" in x.lower())
    df_train["is_custom"] = (df_train["is_custom"] == True) | ser_is_cv  # noqa

    # make nan and None the same
    df_train = df_train.fillna("None")

    df_train = df_train.drop(
        columns=["year_month", "id", "plant_name"]
    )  # id is a duplicate of plant_id

    # plant id should be considered a category, not a number
    df_train["plant_id"] = df_train["plant_id"].astype("category")

    # finally, separate the target variable
    ser_targets_train = df_train["flowering"]
    df_train["species"] = df_train["species"].astype("category")
    df_train["genus"] = df_train["genus"].astype("category")
    df_train = df_train.drop(columns=["flowering"])
    return df_train, ser_targets_train


def add_potting_info(df_train: pd.DataFrame, df_event: pd.DataFrame) -> pd.DataFrame:  # noqa
    """for each entry in df_train, we try to find the current pot's diameter"""
    # we need onyl repotting events
    df_event = df_event[df_event["diameter_width"].notna()]
    df_event = df_event.sort_values("date")
    # loop through the events by plant_id

    results: list[tuple[int, datetime.date, int]] = []
    for plant_id, df_event_plant in df_event.groupby("plant_id"):
        first_repotting: str = df_event_plant.iloc[0]['date']  # yyyy-mm-dd
        # for each month from first repotting to today, we look for the pot diameter
        first_repotting_date = datetime.strptime(first_repotting, "%Y-%m-%d").date()
        # for pd.date_range to start with first month, we need to set the day to 1
        first_repotting_date = first_repotting_date.replace(day=1)

        today = date.today()
        for month in pd.date_range(start=first_repotting_date, end=today, freq="MS"):
            # get last day of that month
            _last_day = calendar.monthrange(month.year, month.month)[1]
            current_month_last_day = month.replace(day=_last_day)

            # find the last event before this month
            df_event_plant_until_current_month = df_event_plant[
                (df_event_plant["date"] <= current_month_last_day.strftime("%Y-%m-%d"))
            ]
            if not df_event_plant_until_current_month.empty:
                # get the last event's diameter
                diameter = df_event_plant_until_current_month.iloc[-1]["diameter_width"]
                results.append((plant_id, month.date(), diameter))
    df_results = pd.DataFrame(
        results, columns=["plant_id", "pot_year_month", "pot_diameter"]
    )
    df_results["pot_year_month"] = pd.to_datetime(df_results["pot_year_month"])

    df_train = df_train.merge(
        df_results,
        how="left",
        left_on=["plant_id", "year_month"],
        right_on=["plant_id", "pot_year_month"],
        suffixes=("", "_potting"),
    )
    return df_train


def assemble_training_data() -> tuple[pd.DataFrame, pd.Series]:
    # df_florescence = pd.read_pickle('/temp/florescence.pkl')
    # df_plant = pd.read_pickle('/temp/plant.pkl')
    # loop = asyncio.get_event_loop()
    # result = loop.run_until_complete(assemble_florescence_data())
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    df_florescence, df_plant, df_event = asyncio.run(assemble_florescence_data())
    # df_florescence.to_pickle('/temp/florescence.pkl')
    # df_plant.to_pickle('/temp/plant.pkl')
    # df_event.to_pickle('/temp/event.pkl')

    plant_id_to_first_last_date = get_first_last_date_per_plant(df_plant, df_event, df_florescence)
    plant_id_to_flowering_months = flowering_months_per_plant(
        list(plant_id_to_first_last_date.keys()), df_florescence
    )
    df_train = get_plant_to_month_targets(plant_id_to_first_last_date, plant_id_to_flowering_months)

    df_train = add_potting_info(df_train, df_event)
    df_train, ser_targets_train = add_features(df_train, df_plant)

    return df_train, ser_targets_train


if __name__ == "__main__":
    # # df_florescence = pd.read_pickle('/temp/florescence.pkl')
    # # df_plant = pd.read_pickle('/temp/plant.pkl')
    # # loop = asyncio.get_event_loop()
    # # result = loop.run_until_complete(assemble_florescence_data())
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    #
    # df_florescence, df_plant, df_event = asyncio.run(assemble_florescence_data())
    # # df_florescence.to_pickle('/temp/florescence.pkl')
    # # df_plant.to_pickle('/temp/plant.pkl')
    # # df_event.to_pickle('/temp/event.pkl')
    #
    # plant_id_to_first_last_date = get_first_last_date_per_plant(df_plant)
    # plant_id_to_flowering_months = flowering_months_per_plant(list(plant_id_to_first_last_date.keys()))
    # df_train = get_plant_to_month_targets(plant_id_to_first_last_date)
    #
    # df_train, ser_targets_train = get_training_data(df_train, df_plant)

    df_train, ser_targets_train = assemble_training_data()

    # train xgb model using cv (3 folds)

    kfold = KFold(n_splits=3, shuffle=True, random_state=42)
    model = XGBClassifier(
        n_estimators=1000,
        # max_depth=6,
        learning_rate=0.1,
        eval_metric="auc",
        verbosity=0,
        # early stopping
        early_stopping_rounds=50,
        objective="binary:logistic",
        enable_categorical=True,
    )
    iterations = []
    for train_index, val_index in kfold.split(df_train):
        X_train, X_val = df_train.iloc[train_index], df_train.iloc[val_index]
        y_train, y_val = ser_targets_train.iloc[train_index], ser_targets_train.iloc[val_index]
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        score = roc_auc_score(y_val, model.predict_proba(X_val)[:, 1])
        best_iter = model.best_iteration
        iterations.append(best_iter)
        print(f"Fold score: {score:.4f}, Best Iteration: {best_iter}")

    # retrain on full data
    print(int(np.mean(iterations)))
    model.n_estimators = int(np.mean(iterations))
    model.early_stopping_rounds = None
    model.fit(df_train, ser_targets_train)
