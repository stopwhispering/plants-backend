from fastapi import Depends
from sqlalchemy.orm import Session

from plants.extensions import orm
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.pollination.florescence_dal import FlorescenceDAL
from plants.modules.pollination.models import Pollination, Florescence
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.modules.taxon.models import Taxon


def get_db():
    db = orm.SessionFactory.create_session()
    try:
        yield db
    finally:
        db.commit()
        db.close()


def get_pollination_dal(db: Session = Depends(get_db)):
    return PollinationDAL(db)


def get_florescence_dal(db: Session = Depends(get_db)):
    return FlorescenceDAL(db)


def get_plant_dal(db: Session = Depends(get_db)):
    return PlantDAL(db)


async def valid_plant(plant_id: int, db: Session = Depends(get_db)) -> Plant:
    """injects a plant orm object into the route function if plant_id is valid"""
    plant = Plant.by_id(plant_id, db, raise_if_not_exists=True)
    return plant


async def valid_pollination(pollination_id: int, db: Session = Depends(get_db)) -> Pollination:
    """injects a pollination orm object into the route function if pollination_id is valid"""
    pollination = Pollination.by_id(pollination_id, db, raise_if_not_exists=True)
    return pollination


async def valid_florescence(florescence_id: int, db: Session = Depends(get_db)) -> Florescence:
    """injects a florescence orm object into the route function if florescence_id is valid"""
    florescence = Florescence.by_id(florescence_id, db, raise_if_not_exists=True)
    return florescence


async def valid_taxon(taxon_id: int, db: Session = Depends(get_db)) -> Taxon:
    """injects a taxon orm object into the route function if taxon_id is valid"""
    taxon = Taxon.by_id(taxon_id, db, raise_if_not_exists=True)
    return taxon
