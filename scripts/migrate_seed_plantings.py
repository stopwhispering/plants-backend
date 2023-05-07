from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from dateutil import relativedelta
from sqlalchemy import select

from plants import local_config
from plants.extensions import orm
from plants.extensions.db import create_db_engine
from plants.extensions.orm import init_orm
from plants.modules.plant.models import Plant
from plants.modules.pollination.enums import PollinationStatus, SeedPlantingStatus
from plants.modules.pollination.models import Pollination, SeedPlanting

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _successful_seed_planting_from_pollination(pollination: Pollination) -> SeedPlanting:
    germinated_first_on = (
        pollination.harvest_date
        + relativedelta.relativedelta(days=1 + pollination.days_until_first_germination)
        if (pollination.days_until_first_germination and pollination.harvest_date)
        else None
    )
    if not pollination.harvest_date:
        raise ValueError
    return SeedPlanting(
        status=SeedPlantingStatus.GERMINATED,
        pollination_id=pollination.id,
        comment=(
            "Imported from pollination record, dates estimated, comment: "
            + (pollination.comment if pollination.comment else "")
        ),
        sterilized=None,
        soaked=None,
        covered=None,
        planted_on=pollination.harvest_date + relativedelta.relativedelta(days=1),
        germinated_first_on=germinated_first_on,
        count_planted=pollination.first_seeds_sown,
        count_germinated=pollination.first_seeds_germinated,
        soil_id=None,
    )


def _abandoned_seed_planting_from_pollination(pollination: Pollination) -> SeedPlanting:
    if not pollination.harvest_date:
        raise ValueError
    if (
        pollination.germination_rate
        or pollination.days_until_first_germination
        or pollination.first_seeds_sown
        or pollination.first_seeds_germinated
    ):
        raise ValueError
    return SeedPlanting(
        status=SeedPlantingStatus.ABANDONED,
        pollination_id=pollination.id,
        comment=(
            "Imported from pollination record, dates estimated, comment: "
            + (pollination.comment if pollination.comment else "")
        ),
        sterilized=None,
        soaked=None,
        covered=None,
        planted_on=pollination.harvest_date + relativedelta.relativedelta(days=1),
        germinated_first_on=None,
        count_planted=None,
        count_germinated=None,
        soil_id=None,
    )


async def create_seed_plantings(session: AsyncSession) -> list[SeedPlanting]:  # noqa: C901,PLR0912
    query = select(Pollination)
    pollinations = (await session.scalars(query)).all()
    pollination: Pollination
    seed_plantings: list[SeedPlanting] = []
    abandoned: list[SeedPlanting] = []
    for pollination in pollinations:
        if pollination.ongoing is True:
            if (
                pollination.days_until_first_germination
                or pollination.first_seeds_sown
                or pollination.first_seeds_germinated
                or pollination.germination_rate
            ):
                raise ValueError
            continue

        if pollination.pollination_status == PollinationStatus.ATTEMPT:
            if (
                pollination.days_until_first_germination
                or pollination.first_seeds_sown
                or pollination.first_seeds_germinated
                or pollination.germination_rate
            ):
                raise ValueError
            continue

        if pollination.pollination_status == PollinationStatus.SEED_CAPSULE:
            if (
                pollination.days_until_first_germination
                or pollination.germination_rate
                or pollination.first_seeds_sown
            ):
                raise ValueError
            continue

        if pollination.pollination_status == PollinationStatus.SELF_POLLINATED:
            if not pollination.harvest_date:
                print(f"Skipping (no harvest date): {pollination}")
                continue

            seed_plantings.append(_successful_seed_planting_from_pollination(pollination))
        elif pollination.pollination_status == PollinationStatus.UNKNOWN:
            raise ValueError
        elif pollination.pollination_status == PollinationStatus.GERMINATED:
            if (
                pollination.days_until_first_germination is None
                and not pollination.first_seeds_sown
                and not pollination.first_seeds_germinated
                and not pollination.harvest_date
            ):
                if not pollination.harvest_date:
                    print(f"Skipping (no harvest date): {pollination}")
                    continue
                if pollination.id in (488, 489):
                    print(f"Skipping inconsistent pollination {pollination}")
                    continue
                raise ValueError
            s = _successful_seed_planting_from_pollination(pollination)
            seed_plantings.append(s)
        elif pollination.pollination_status == PollinationStatus.SEED:
            if (
                pollination.days_until_first_germination
                or pollination.first_seeds_sown
                or pollination.first_seeds_germinated
                or pollination.germination_rate
            ):
                raise ValueError

            if not pollination.harvest_date:
                print(f"Skipping abandoned (no harvest date): {pollination}")
                continue
            s = _abandoned_seed_planting_from_pollination(pollination)
            abandoned.append(s)

        else:
            raise ValueError
    print(f"Successful Seed Plantings: {len(seed_plantings)}")
    print(f"Abandoned Seed Plantings: {len(abandoned)}")

    return seed_plantings + abandoned


async def save(session: AsyncSession, seed_plantings: list[SeedPlanting]) -> None:
    session.add_all(seed_plantings)
    await session.flush()


async def migrate() -> None:
    engine = create_db_engine(local_config.connection_string)
    async with engine.begin() as conn:
        await init_orm(engine=conn)
        session = orm.SessionFactory.create_session()

        seed_plantings = await create_seed_plantings(session)

        await save(session, seed_plantings)
        # await session.commit()


asyncio.run(migrate())
