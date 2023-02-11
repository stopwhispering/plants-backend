from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from plants.extensions import orm
from plants.modules.event.event_dal import EventDAL
from plants.shared.history_dal import HistoryDAL
from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.property.property_dal import PropertyDAL
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.modules.pollination.florescence_dal import FlorescenceDAL
from plants.modules.pollination.models import Pollination, Florescence
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.modules.taxon.models import Taxon


async def get_db():
    """generator for db sessions"""
    async with orm.SessionFactory.create_session() as db:
        yield db


def get_pollination_dal(db: AsyncSession = Depends(get_db)):
    return PollinationDAL(db)


def get_florescence_dal(db: AsyncSession = Depends(get_db)):
    return FlorescenceDAL(db)


def get_property_dal(db: AsyncSession = Depends(get_db)):
    return PropertyDAL(db)


def get_history_dal(db: AsyncSession = Depends(get_db)):
    return HistoryDAL(db)


def get_image_dal(db: AsyncSession = Depends(get_db)):
    return ImageDAL(db)


def get_plant_dal(db: AsyncSession = Depends(get_db)):
    return PlantDAL(db)


def get_taxon_dal(db: AsyncSession = Depends(get_db)):
    return TaxonDAL(db)


def get_event_dal(db: AsyncSession = Depends(get_db)):
    return EventDAL(db)


async def valid_plant(plant_id: int, plant_dal: PlantDAL = Depends(get_plant_dal)) -> Plant:
    """injects a plant orm object into the route function if plant_id is valid"""
    plant = await plant_dal.by_id(plant_id)
    return plant


async def valid_pollination(pollination_id: int,
                            pollination_dal: PollinationDAL = Depends(get_pollination_dal)) -> Pollination:
    """injects a pollination orm object into the route function if pollination_id is valid"""
    pollination = await pollination_dal.by_id(pollination_id)
    return pollination


async def valid_florescence(florescence_id: int,
                            florescence_dal: FlorescenceDAL = Depends(get_florescence_dal)) -> Florescence:
    """injects a florescence orm object into the route function if florescence_id is valid"""
    florescence = await florescence_dal.by_id(florescence_id)
    return florescence


async def valid_taxon(taxon_id: int, taxon_dal: TaxonDAL = Depends(get_taxon_dal)) -> Taxon:
    """injects a taxon orm object into the route function if taxon_id is valid"""
    taxon = await taxon_dal.by_id(taxon_id)
    return taxon
