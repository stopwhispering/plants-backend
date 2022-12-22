import logging
from sqlalchemy.orm import Session

from plants.models.event_models import Soil
from plants.util.ui_utils import throw_exception
from plants.validation.event_validation import PRSoil, PSoilCreate

logger = logging.getLogger(__name__)


def create_soil(soil: PSoilCreate, db: Session) -> Soil:
    """create new soil in database"""
    if soil.id:
        throw_exception(f'Soil already exists: {soil.id}')

    # make sure there isn't a soil yet with same name
    soil_obj = db.query(Soil).filter(Soil.soil_name == soil.soil_name.strip()).first()
    if soil_obj:
        throw_exception(f'Soil already exists: {soil.soil_name.strip()}')

    soil_obj = Soil(soil_name=soil.soil_name,
                    mix=soil.mix,
                    description=soil.description)
    db.add(soil_obj)
    db.commit()
    logger.info(f'Created soil {soil_obj.id} - {soil_obj.soil_name}')
    return soil_obj


def update_soil(soil: PRSoil, db: Session) -> Soil:
    """update existing soil in database"""
    # make sure there isn't another soil with same name
    soil_obj_same_name = db.query(Soil).filter((Soil.soil_name == soil.soil_name.strip()) & (Soil.id != soil.id)).all()
    if soil_obj_same_name:
        throw_exception(f'Soil with that name already exists: {soil.soil_name.strip()}')

    soil_obj: Soil = db.query(Soil).filter(Soil.id == soil.id).first()
    if not soil_obj:
        throw_exception(f'Soil ID {soil.id} does not exists.')

    soil_obj.soil_name = soil.soil_name
    soil_obj.description = soil.description
    soil_obj.mix = soil.mix

    db.commit()
    logger.info(f'Updated soil {soil_obj.id} - {soil_obj.soil_name}')
    return soil_obj
