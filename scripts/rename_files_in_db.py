import asyncio

from sqlalchemy import select

import plants.modules.event.models
import plants.modules.plant.models
import plants.modules.pollination.models
import plants.modules.taxon.models
from plants import local_config
from plants.extensions import orm
from plants.extensions.db import create_db_engine
from plants.extensions.orm import init_orm
from plants.modules.image.models import Image


async def migrate():
    engine = create_db_engine(local_config.connection_string)

    async with engine.begin() as conn:
        await init_orm(engine=conn)
        db = orm.SessionFactory.create_session()

        async with db:
            q = select(Image)
            images = (await db.scalars(q)).all()
            found = 0
            not_found = 0
            fixed = 0
            image: Image
            for image in images:
                p = image.absolute_path
                if p.is_file():
                    found += 1
                else:
                    not_found += 1
                    if not image.absolute_path.name.endswith("jpg"):
                        jpg_path = image.absolute_path.with_suffix(".jpg")
                        if jpg_path.is_file():
                            print(f"Found jpg: {jpg_path}")
                            image.filename = jpg_path.name
                            fixed += 1

            print(f"Found: {found}, not found: {not_found}")
            if fixed:
                await db.commit()
                print(f"Fixed: {fixed}")


asyncio.run(migrate())
