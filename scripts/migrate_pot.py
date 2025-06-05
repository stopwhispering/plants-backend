from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from plants import local_config
from plants.extensions import orm
from plants.extensions.db import create_db_engine
from plants.extensions.orm import init_orm
from plants.modules.event.models import Event, Pot
from plants.modules.plant.models import Plant
from plants.shared.orm_util import clone_orm_instance

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def delete_orphans(session: AsyncSession) -> None:
    query = select(Event.pot_id)
    event_pot_ids = (await session.scalars(query)).all()
    pot_ids = {pot_id for pot_id in event_pot_ids if pot_id is not None}

    query = select(Pot).where(Pot.id.notin_(pot_ids))
    orphaned_pot_records = (await session.scalars(query)).all()

    for pot in orphaned_pot_records:
        await session.delete(pot)

    await session.flush()


async def treat_multiple_events_per_pot(session: AsyncSession) -> None:
    query = select(Event)
    events = (await session.scalars(query)).all()
    event_pot_ids = [event.pot_id for event in events if event.pot_id is not None]
    pot_ids_distinct = set(event_pot_ids)
    new_list = []

    for pot_id in pot_ids_distinct:
        if event_pot_ids.count(pot_id) >= 2:
            events_current_pot = [event for event in events if event.pot_id == pot_id]
            # duplicate the pot record
            query = select(Pot).where(Pot.id == pot_id)
            pot = (await session.scalars(query)).first()
            if pot is None:
                raise ValueError(f"Pot with id {pot_id} not found")
            print(f"Pot {pot} is used by {len(events_current_pot)} events")
            for i in range(len(events_current_pot) - 1):
                pot_clone = clone_orm_instance(pot)
                new_list.append(pot_clone)
                events_current_pot[i + 1].pot = pot_clone

    session.add_all(new_list)
    await session.flush()


async def set_event_id_in_pot_records(session: AsyncSession) -> None:
    query = select(Event).options(selectinload(Event.pot))
    events = (await session.scalars(query)).all()
    for event in events:
        if event.pot is not None:
            pot = event.pot
            pot.event_id = event.id

    await session.flush()


async def migrate():
    engine = create_db_engine(local_config.connection_string)
    async with engine.begin() as conn:
        await init_orm(engine=conn)
        session = orm.SessionFactory.create_session()

        # delete orphaned pot records (no corresponding event)
        await delete_orphans(session)

        # a few pot records are used by multiple events, differing only in plant_id
        await treat_multiple_events_per_pot(session)

        # set event_id in pot records
        await set_event_id_in_pot_records(session)

        # query = select(Pot)
        # plants = (await session.scalars(query)).all()
        # plants = cast(list[Plant], plants)
        #
        # for plant in plants:
        #     if not plant.filename_previewimage:
        #         continue
        #
        #     query = select(Image).where(Image.filename == plant.filename_previewimage)
        #     image = (await session.scalars(query)).first()
        #     if not image:
        #         continue
        #     image: Image = cast(Image, image)
        #     plant.preview_image = image
        #
        # await session.flush()
        # await session.commit()


asyncio.run(migrate())
