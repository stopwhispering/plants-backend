from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from plants import local_config
from plants.modules.event.models import Event, Pot
from plants.modules.plant.models import Plant
from plants.modules.pollination.models import Florescence
from plants.modules.taxon.models import Taxon

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    # from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
    #     FeatureContainer,
    # )


async def _read_florescences_with_plants_and_taxa() -> pd.DataFrame:
    """Read and merge florescences with their plants and taxa."""

    def read_data(
        session: Session,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        conn = session.connection()
        df_florescence = pd.read_sql_query(sql=sqlalchemy.select(Florescence), con=conn)
        df_plant = pd.read_sql_query(sql=sqlalchemy.select(Plant), con=conn)
        df_taxon = pd.read_sql_query(sql=sqlalchemy.select(Taxon), con=conn)
        return df_florescence, df_plant, df_taxon

    engine = create_async_engine(local_config.connection_string)

    # async with engine.begin() as conn:
    session: AsyncSession
    async with AsyncSession(engine) as session:
        df_florescence, df_plant, df_taxon = await session.run_sync(read_data)

    # inner join plant
    if df_florescence["plant_id"].isna().any():
        raise ValueError("Florescence without plant_id")
    df_merged1 = df_florescence.merge(
        df_plant,
        how="inner",
        left_on=["plant_id"],
        right_on=["id"],
        suffixes=(None, "_plant"),
        validate="many_to_one",  # raise if merge key not unique on right side
    )
    df_merged1 = df_merged1.drop(["id_plant"], axis=1)

    # left outer join taxon; joining table key, so count is unchanged
    df_merged2 = df_merged1.merge(
        df_taxon,
        how="left",
        left_on=["taxon_id"],
        right_on=["id"],
        suffixes=(None, "_taxon"),
        validate="many_to_one",  # raise if not unique on right side
    )
    return df_merged2.drop(["id_taxon", "last_updated_at_taxon", "created_at_taxon"], axis=1)


async def _read_plants_with_events() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read plants with their taxa and events from the database.

    This includes plants that have no florescence.
    """

    def read_data(
        session: Session,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        conn = session.connection()
        df_plant = pd.read_sql_query(sql=sqlalchemy.select(Plant), con=conn)
        df_taxon = pd.read_sql_query(sql=sqlalchemy.select(Taxon), con=conn)
        df_event = pd.read_sql_query(sql=sqlalchemy.select(Event), con=conn)
        df_pot = pd.read_sql_query(sql=sqlalchemy.select(Pot), con=conn)

        return df_plant, df_taxon, df_event, df_pot

    engine = create_async_engine(local_config.connection_string)

    # async with engine.begin() as conn:
    session: AsyncSession
    async with AsyncSession(engine) as session:
        df_plant, df_taxon, df_event, df_pot = await session.run_sync(read_data)

    # left outer join taxon; joining table key, so count is unchanged
    df_merged1 = df_plant.merge(
        df_taxon,
        how="left",
        left_on=["taxon_id"],
        right_on=["id"],
        suffixes=(None, "_taxon"),
        validate="many_to_one",  # raise if not unique on right side
    )
    df_merged1 = df_merged1.drop(["id_taxon", "last_updated_at_taxon", "created_at_taxon"], axis=1)

    # discard events that are not associated with a plant in df_plant
    df_event = df_event[df_event["plant_id"].isin(df_plant["id"])]

    # left outer join repottings; # joining table key, so count is unchanged
    df_event_merged = df_event.merge(
        df_pot[["event_id", "material", "shape_top", "shape_side", "diameter_width"]],
        how="left",
        left_on=["id"],
        right_on=["event_id"],
        suffixes=(None, "_pot"),
        validate="many_to_one",  # raise if not unique on right side
    )
    df_event_merged = df_event_merged.drop(["event_id"], axis=1)

    return df_merged1, df_event_merged


async def assemble_florescence_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df_florescence = await _read_florescences_with_plants_and_taxa()
    df_plant, df_event = await _read_plants_with_events()

    return df_florescence, df_plant, df_event
