from __future__ import annotations

import asyncio
from typing import cast

from sqlalchemy import select

from plants import local_config
from plants.extensions import orm
from plants.extensions.db import create_db_engine
from plants.extensions.orm import init_orm
from plants.modules.image.models import Image
from plants.modules.plant.models import Plant


async def migrate():
    engine = create_db_engine(local_config.connection_string)
    async with engine.begin() as conn:
        await init_orm(engine=conn)
        session = orm.SessionFactory.create_session()

        query = select(Plant)
        plants = (await session.scalars(query)).all()
        plants = cast(list[Plant], plants)

        for plant in plants:
            if not plant.filename_previewimage:
                continue

            query = select(Image).where(Image.filename == plant.filename_previewimage)
            image = (await session.scalars(query)).first()
            if not image:
                continue
            image: Image = cast(Image, image)
            plant.preview_image = image

        await session.flush()
        await session.commit()


asyncio.run(migrate())
