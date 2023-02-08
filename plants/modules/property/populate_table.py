from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from plants import constants
from plants.modules.property.models import PropertyCategory, logger


async def insert_property_categories(db: AsyncSession):
    # add Trait Categories if not existing upon initializing
    for t in constants.PROPERTY_CATEGORIES:
        query = select(PropertyCategory).where(PropertyCategory.category_name == t)
        property_category = (await db.execute(query)).scalars().first()  # noqa
        if not property_category:
            logger.info(f'Inserting missing trait category into db: {t}')
            property_category = PropertyCategory(category_name=t)
            db.add(property_category)
    await db.commit()
