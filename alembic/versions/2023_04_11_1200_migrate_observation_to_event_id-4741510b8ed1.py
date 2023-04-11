"""Migrate observation to event_id.

Revision ID: 4741510b8ed1
Revises: 0a67da44d9c8
Create Date: 2023-04-11 12:00:11.775516
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from plants.modules.event.models import Event, Observation
from plants.modules.plant.models import Plant
from plants.shared.orm_util import clone_orm_instance

# revision identifiers, used by Alembic.
revision = "4741510b8ed1"
down_revision = "0a67da44d9c8"
branch_labels = None
depends_on = None


def delete_orphans(session: AsyncSession) -> None:
    query = select(Event.observation_id)
    event_observation_ids = (session.scalars(query)).all()
    observation_ids = {obs_id for obs_id in event_observation_ids if obs_id is not None}

    query = select(Observation).where(Observation.id.notin_(observation_ids))
    orphaned_observation_records = (session.scalars(query)).all()

    for observation in orphaned_observation_records:
        session.delete(observation)

    session.flush()


def treat_multiple_events_per_observation(session: AsyncSession) -> None:
    query = select(Event)
    events = (session.scalars(query)).all()
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
            observation = (session.scalars(query)).first()
            if observation is None:
                raise ValueError(f"observation with id {observation_id} not found")
            print(
                f"observation {observation} is used by {len(events_current_observation)} events"
            )
            for i in range(len(events_current_observation) - 1):
                observation_clone = clone_orm_instance(observation)
                new_list.append(observation_clone)
                events_current_observation[i + 1].observation = observation_clone

    session.add_all(new_list)
    session.flush()


def set_event_id_in_observation_records(session: AsyncSession) -> None:
    query = select(Event).options(selectinload(Event.observation))
    events = (session.scalars(query)).all()
    for event in events:
        if event.observation is not None:
            observation = event.observation
            observation.event_id = event.id

    session.flush()


def migrate_observation(session: AsyncSession) -> None:
    # engine = create_db_engine(local_config.connection_string)
    # async with engine.begin() as conn:
    #     await init_orm(engine=conn)
    #     session = orm.SessionFactory.create_session()

    # delete orphaned observation records (no corresponding event)
    delete_orphans(session)
    # await session.rollback()

    # a few observation records are used by multiple events, differing only in plant_id
    treat_multiple_events_per_observation(session)
    # await session.rollback()

    # set event_id in observation records
    set_event_id_in_observation_records(session)
    # await session.rollback()


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("observation", sa.Column("event_id", sa.INTEGER(), nullable=True))
    session = Session(bind=op.get_bind())
    migrate_observation(session)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("observation", "event_id")
    # ### end Alembic commands ###
