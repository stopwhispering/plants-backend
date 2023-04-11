from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from plants import local_config
from plants.extensions import orm
from plants.extensions.db import create_db_engine
from plants.extensions.orm import init_orm
from plants.modules.event.models import Event, Observation
from plants.modules.plant.models import Plant
from plants.shared.orm_util import clone_orm_instance

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def delete_orphans(session: AsyncSession) -> None:
    query = select(Event.observation_id)
    event_observation_ids = (await session.scalars(query)).all()
    observation_ids = {obs_id for obs_id in event_observation_ids if obs_id is not None}

    query = select(Observation).where(Observation.id.notin_(observation_ids))
    orphaned_observation_records = (await session.scalars(query)).all()

    for observation in orphaned_observation_records:
        await session.delete(observation)

    await session.flush()


async def treat_multiple_events_per_observation(session: AsyncSession) -> None:
    query = select(Event)
    events = (await session.scalars(query)).all()
    event_observation_ids = [
        event.observation_id for event in events if event.observation_id is not None
    ]
    observation_ids_distinct = set(event_observation_ids)
    new_list = []

    for observation_id in observation_ids_distinct:
        if event_observation_ids.count(observation_id) >= 2:
            events_current_observation = [
                event for event in events if event.observation_id == observation_id
            ]
            # duplicate the observation record
            query = select(Observation).where(Observation.id == observation_id)
            observation = (await session.scalars(query)).first()
            if observation is None:
                raise ValueError(f"observation with id {observation_id} not found")
            print(
                f"observation {observation} is used by "
                f"{len(events_current_observation)} events"
            )
            for i in range(len(events_current_observation) - 1):
                observation_clone = clone_orm_instance(observation)
                new_list.append(observation_clone)
                events_current_observation[i + 1].observation = observation_clone

    session.add_all(new_list)
    await session.flush()


async def set_event_id_in_observation_records(session: AsyncSession) -> None:
    query = select(Event).options(selectinload(Event.observation))
    events = (await session.scalars(query)).all()
    for event in events:
        if event.observation is not None:
            observation = event.observation
            observation.event_id = event.id

    await session.flush()


async def migrate_observation():
    engine = create_db_engine(local_config.connection_string)
    async with engine.begin() as conn:
        await init_orm(engine=conn)
        session = orm.SessionFactory.create_session()

        # delete orphaned observation records (no corresponding event)
        await delete_orphans(session)
        await session.rollback()

        # a few observation records are used by multiple events,
        # differing only in plant_id
        await treat_multiple_events_per_observation(session)
        await session.rollback()

        # set event_id in observation records
        await set_event_id_in_observation_records(session)
        await session.rollback()


# asyncio.run(migrate_observation())  # run in alembic!
