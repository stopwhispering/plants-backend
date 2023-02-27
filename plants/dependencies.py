from __future__ import annotations

from fastapi import Depends

# if TYPE_CHECKING:
from sqlalchemy.ext.asyncio import AsyncSession

from plants.extensions import orm
from plants.modules.event.event_dal import EventDAL
from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.pollination.florescence_dal import FlorescenceDAL
from plants.modules.pollination.models import Florescence, Pollination
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.modules.taxon.models import Taxon
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.history_dal import HistoryDAL


async def get_db():
    """Generator for db sessions."""
    # async with orm.SessionFactory.create_session() as db:
    db = orm.SessionFactory.create_session()
    try:
        yield db
    except:  # noqa
        await db.rollback()
    finally:
        await db.commit()
        await db.close()


def get_pollination_dal(db: AsyncSession = Depends(get_db)):
    return PollinationDAL(db)


def get_florescence_dal(db: AsyncSession = Depends(get_db)):
    return FlorescenceDAL(db)


def get_history_dal(db: AsyncSession = Depends(get_db)):
    return HistoryDAL(db)


def get_image_dal(db: AsyncSession = Depends(get_db)):
    return ImageDAL(db)


def get_plant_dal(db: AsyncSession = Depends(get_db)):
    return PlantDAL(db)


def get_taxon_dal(db: AsyncSession = Depends(get_db)) -> TaxonDAL:
    return TaxonDAL(db)


def get_event_dal(db: AsyncSession = Depends(get_db)):
    return EventDAL(db)


async def valid_plant(
    plant_id: int, plant_dal: PlantDAL = Depends(get_plant_dal)
) -> Plant:
    """Injects a plant orm object into the route function if plant_id is valid."""
    return await plant_dal.by_id(plant_id)


async def valid_pollination(
    pollination_id: int, pollination_dal: PollinationDAL = Depends(get_pollination_dal)
) -> Pollination:
    """Injects a pollination orm object into the route function if pollination_id is
    valid."""
    return await pollination_dal.by_id(pollination_id)


async def valid_florescence(
    florescence_id: int, florescence_dal: FlorescenceDAL = Depends(get_florescence_dal)
) -> Florescence:
    """Injects a florescence orm object into the route function if florescence_id is
    valid."""
    return await florescence_dal.by_id(florescence_id)


async def valid_taxon(
    taxon_id: int, taxon_dal: TaxonDAL = Depends(get_taxon_dal)
) -> Taxon:
    """Injects a taxon orm object into the route function if taxon_id is valid."""
    return await taxon_dal.by_id(taxon_id)
