from __future__ import annotations

import asyncio
from datetime import datetime

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from plants import local_config
from plants.extensions.db import create_db_engine
from plants.extensions.orm import init_orm
from plants.modules.event.models import Event
from plants.modules.plant.models import Plant
from plants.modules.pollination.prediction.predict_florescence import \
    predict_probability_of_florescence
from plants.modules.pollination.prediction.train_florescence import assemble_training_data, \
    train_and_pickle_xgb_florescence_model
from plants.extensions import orm

def experiment_train():
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    df_train, ser_targets_train = asyncio.run(assemble_training_data())
    print(df_train.shape)
    estimator, metric_name, metric_value = train_and_pickle_xgb_florescence_model(df_train, ser_targets_train)


async def get_plant(plant_id) -> Plant:
    engine = create_db_engine(local_config.connection_string)
    async with engine.begin() as conn:
        await init_orm(engine=conn)
        # session = orm.SessionFactory.create_session()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:

            query = select(Plant).where(Plant.id == plant_id)

            # make sure plant.events and its pots are loaded
            query = query.options(
                joinedload(Plant.events)
                .joinedload(Event.pot),
                joinedload(Plant.taxon)
            )
            plant = (await session.scalars(query)).first()

            return plant


async def get_plants() -> list[Plant]:
    engine = create_db_engine(local_config.connection_string)
    async with engine.begin() as conn:
        await init_orm(engine=conn)
        # session = orm.SessionFactory.create_session()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:

            query = select(Plant)

            # make sure plant.events and its pots are loaded
            query = query.options(
                joinedload(Plant.events)
                .joinedload(Event.pot),
                joinedload(Plant.taxon)
            )
            plants = (await session.scalars(query)).unique().all()

            return plants


async def experiment_predict():
    # plant = await get_plant(940)  # 940 -> Gasteria armstrongii VI
    plant = await get_plant(989)  # 940 -> Haworthia cooperi
    year_month_proba = predict_probability_of_florescence(plant)
    df_results = pd.DataFrame(year_month_proba, columns=["year", "month", "probability"])
    with pd.option_context('display.max_columns', None):
        print(df_results)


async def experiment_find_high_proba_plant():
    plants = await get_plants()
    results = []
    for plant in plants:
        year_month_proba = predict_probability_of_florescence(plant)
        for year, month, probability in year_month_proba:
            results.append((plant.id, plant.plant_name, year, month, probability))

    results.sort(key=lambda x: x[-1], reverse=True)
    df_results = pd.DataFrame(results, columns=["plant_id", "plant_name", "year", "month", "probability"])
    with pd.option_context('display.max_columns', None):
        print(df_results)


if __name__ == "__main__":
    # experiment_train()

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(experiment_predict())
    # asyncio.run(experiment_find_high_proba_plant())




