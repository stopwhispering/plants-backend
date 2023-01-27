from __future__ import annotations

from sqlalchemy.orm import Session

from plants import constants
from plants.modules.property.models import PropertyCategory, logger


def insert_property_categories(db: Session):
    # add Trait Categories if not existing upon initializing
    for t in constants.PROPERTY_CATEGORIES:
        property_category = db.query(PropertyCategory).filter(PropertyCategory.category_name == t).first()
        if not property_category:
            logger.info(f'Inserting missing trait category into db: {t}')
            property_category = PropertyCategory(category_name=t)
            db.add(property_category)
    db.commit()
