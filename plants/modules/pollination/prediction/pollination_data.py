from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from plants import local_config
from plants.modules.plant.models import Plant
from plants.modules.pollination.models import Florescence, Pollination
from plants.modules.taxon.models import Taxon

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from plants.modules.pollination.prediction.ml_helpers.preprocessing.features import (
        FeatureContainer,
    )


async def _read_db_and_join() -> pd.DataFrame:
    # read from db into dataframe
    # i feel more comfortable with joining dataframes than with sqlalchemy...
    # todo rework data access completely!!!

    def read_data(
        session: Session,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        conn = session.connection()

        # noinspection PyTypeChecker
        df_pollination = pd.read_sql_query(
            sql=sqlalchemy.select(Pollination).filter(
                # ~Pollination.ongoing,
                Pollination.pollination_status != "self_pollinated",
            ),
            con=conn,
        )

        df_florescence = pd.read_sql_query(sql=sqlalchemy.select(Florescence), con=conn)
        df_plant = pd.read_sql_query(sql=sqlalchemy.select(Plant), con=conn)
        df_taxon = pd.read_sql_query(sql=sqlalchemy.select(Taxon), con=conn)
        return df_pollination, df_florescence, df_plant, df_taxon

    engine = create_async_engine(local_config.connection_string)

    # async with engine.begin() as conn:
    session: AsyncSession
    async with AsyncSession(engine) as session:
        df_pollination, _, df_plant, df_taxon = await session.run_sync(read_data)

    # merge with florescences
    # todo un-un-comment once enough data
    df_merged = df_pollination
    # df_merged = df_pollination.merge(
    #     df_florescence[["id", "branches_count", "flowers_count", "avg_ripening_time"]],
    #     how="left",
    #     left_on=["florescence_id"],
    #     right_on=["id"],
    #     validate="many_to_one",  # raise if not unique on right side
    # )

    # merge with plants for seed capsule
    df_merged2 = df_merged.merge(
        df_plant[["id", "taxon_id"]],
        how="left",
        left_on=["seed_capsule_plant_id"],
        right_on=["id"],
        suffixes=(None, "_seed_capsule"),
        validate="many_to_one",
    )  # raise if not unique on right side
    df_merged2 = df_merged2.rename({"taxon_id": "taxon_id_seed_capsule"}, axis=1)

    # merge with plants for pollen donor
    df_merged3 = df_merged2.merge(
        df_plant[["id", "taxon_id"]],
        how="left",
        left_on=["pollen_donor_plant_id"],
        right_on=["id"],
        suffixes=(None, "_pollen_donor"),
        validate="many_to_one",
    )  # raise if not unique on right side
    df_merged3 = df_merged3.rename({"taxon_id": "taxon_id_pollen_donor"}, axis=1)

    # merge with taxon for seed capsule
    df_merged4 = df_merged3.merge(
        df_taxon[["id", "genus", "species", "hybrid", "hybridgenus"]],
        how="left",
        left_on=["taxon_id_seed_capsule"],
        right_on=["id"],
        suffixes=(None, "_seed_capsule"),
        validate="many_to_one",
    )  # raise if not unique on right side
    df_merged4 = df_merged4.rename(
        {
            "genus": "genus_seed_capsule",
            "species": "species_seed_capsule",
            "hybrid": "hybrid_seed_capsule",
            "hybridgenus": "hybridgenus_seed_capsule",
        },
        axis=1,
    )

    # merge with taxon for pollen donor
    df_final: pd.DataFrame = df_merged4.merge(
        df_taxon[["id", "genus", "species", "hybrid", "hybridgenus"]],
        how="left",
        left_on=["taxon_id_pollen_donor"],
        right_on=["id"],
        suffixes=(None, "_pollen_donor"),
        validate="many_to_one",
    )  # raise if not unique on right side
    return df_final.rename(
        {
            "genus": "genus_pollen_donor",
            "species": "species_pollen_donor",
            "hybrid": "hybrid_pollen_donor",
            "hybridgenus": "hybridgenus_pollen_donor",
        },
        axis=1,
    )


async def assemble_pollination_data(feature_container: FeatureContainer) -> pd.DataFrame:
    df_all = await _read_db_and_join()

    # add some custom features
    df_all["same_genus"] = df_all["genus_pollen_donor"] == df_all["genus_seed_capsule"]
    df_all["same_species"] = df_all["species_pollen_donor"] == df_all["species_seed_capsule"]

    if missing := [f for f in feature_container.get_columns() if f not in df_all.columns]:
        raise ValueError(f"Feature(s) not in dataframe: {missing}")

    return df_all
