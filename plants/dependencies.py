from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

# if TYPE_CHECKING:
from sqlalchemy.ext.asyncio import AsyncSession

from plants.extensions import orm
from plants.modules.event.event_dal import EventDAL
from plants.modules.image.image_dal import ImageDAL
from plants.modules.image.models import Image
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.pollination.florescence_dal import FlorescenceDAL
from plants.modules.pollination.models import Florescence, Pollination, SeedPlanting
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.modules.pollination.seed_planting_dal import SeedPlantingDAL
from plants.modules.taxon.models import Taxon
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.history_dal import HistoryDAL

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Generator for db sessions."""
    # async with orm.SessionFactory.create_session() as db:
    db = orm.SessionFactory.create_session()
    # noinspection PyBroadException
    try:
        yield db
    except:  # noqa: E722
        await db.rollback()
    finally:
        await db.commit()
        await db.close()


def get_pollination_dal(db: AsyncSession = Depends(get_db)) -> PollinationDAL:
    return PollinationDAL(db)


def get_florescence_dal(db: AsyncSession = Depends(get_db)) -> FlorescenceDAL:
    return FlorescenceDAL(db)


def get_seed_planting_dal(db: AsyncSession = Depends(get_db)) -> SeedPlantingDAL:
    return SeedPlantingDAL(db)


def get_history_dal(db: AsyncSession = Depends(get_db)) -> HistoryDAL:
    return HistoryDAL(db)


def get_image_dal(db: AsyncSession = Depends(get_db)) -> ImageDAL:
    return ImageDAL(db)


def get_plant_dal(db: AsyncSession = Depends(get_db)) -> PlantDAL:
    return PlantDAL(db)


def get_taxon_dal(db: AsyncSession = Depends(get_db)) -> TaxonDAL:
    return TaxonDAL(db)


def get_event_dal(db: AsyncSession = Depends(get_db)) -> EventDAL:
    return EventDAL(db)


async def valid_plant(plant_id: int, plant_dal: PlantDAL = Depends(get_plant_dal)) -> Plant:
    """Injects a plant orm object into the route function if plant_id is valid."""
    return await plant_dal.by_id(plant_id)


async def valid_image(image_id: int, image_dal: ImageDAL = Depends(get_image_dal)) -> Image:
    """Injects an image orm object into the route function if image_id is valid."""
    return await image_dal.by_id(image_id)


async def valid_pollination(
    pollination_id: int, pollination_dal: PollinationDAL = Depends(get_pollination_dal)
) -> Pollination:
    """Injects a pollination orm object into the route function if pollination_id is valid."""
    return await pollination_dal.by_id(pollination_id)


async def valid_florescence(
    florescence_id: int, florescence_dal: FlorescenceDAL = Depends(get_florescence_dal)
) -> Florescence:
    """Injects a florescence orm object into the route function if florescence_id is valid."""
    return await florescence_dal.by_id(florescence_id)


async def valid_seed_planting(
    seed_planting_id: int, seed_planting_dal: SeedPlantingDAL = Depends(get_seed_planting_dal)
) -> SeedPlanting:
    """Injects a seed planting orm object into the route function if seed_planting_id is valid."""
    return await seed_planting_dal.by_id(seed_planting_id)


async def valid_taxon(taxon_id: int, taxon_dal: TaxonDAL = Depends(get_taxon_dal)) -> Taxon:
    """Injects a taxon orm object into the route function if taxon_id is valid."""
    return await taxon_dal.by_id(taxon_id)
