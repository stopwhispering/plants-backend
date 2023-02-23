import logging
from collections import defaultdict
from operator import attrgetter
from typing import Optional

from plants.exceptions import SoilNotUnique
from plants.modules.event.event_dal import EventDAL
from plants.modules.event.models import Event, Observation, Pot, Soil
from plants.modules.event.schemas import EventCreateUpdate, SoilCreate, SoilUpdate
from plants.modules.image.image_dal import ImageDAL
from plants.modules.image.models import Image, ImageToEventAssociation
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.shared.message_services import throw_exception

logger = logging.getLogger(__name__)


async def read_events_for_plant(plant: Plant, event_dal: EventDAL) -> list[dict]:
    """
    read events from event database table
    """
    # plant has .events loaded, but not all sub-relationships; therefore, we load them here
    events: list[Event] = await event_dal.get_events_by_plant(plant)
    return events


async def create_soil(soil: SoilCreate, event_dal: EventDAL) -> Soil:
    """create new soil in database"""
    if soil.id:
        throw_exception(f"Soil already exists: {soil.id}")

    # make sure there isn't a soil yet with same name
    same_name_soils = await event_dal.get_soils_by_name(soil.soil_name.strip())
    if same_name_soils:
        raise SoilNotUnique(soil.soil_name.strip())

    soil_obj = Soil(
        soil_name=soil.soil_name, mix=soil.mix, description=soil.description
    )
    await event_dal.create_soil(soil_obj)
    logger.info(f"Created soil {soil_obj.id} - {soil_obj.soil_name}")
    return soil_obj


async def update_soil(soil: SoilUpdate, event_dal: EventDAL) -> Soil:
    """update existing soil in database"""
    # make sure there isn't another soil with same name in case of renaming
    same_name_soils = await event_dal.get_soils_by_name(soil.soil_name.strip())
    same_name_soils = [s for s in same_name_soils if s.id != soil.id]
    if same_name_soils:
        raise SoilNotUnique(soil.soil_name.strip())

    soil_obj: Soil = await event_dal.get_soil_by_id(soil.id)

    await event_dal.update_soil(
        soil_obj,
        {"soil_name": soil.soil_name, "description": soil.description, "mix": soil.mix},
    )

    logger.info(f"Updated soil {soil_obj.id} - {soil_obj.soil_name}")
    return soil_obj


async def create_or_update_event(
    plant_id: int,
    events: list[EventCreateUpdate],
    counts: defaultdict,
    image_dal: ImageDAL,
    event_dal: EventDAL,
    plant_dal: PlantDAL,
) -> None:
    plant_obj = await plant_dal.by_id(plant_id)
    logger.info(
        f"Plant {plant_obj.plant_name} has {len(plant_obj.events)} events in db:"
        f" {[e.id for e in plant_obj.events]}"
    )

    # todo remove that comment if no need
    # event might have no id in browser but already in backend from earlier save
    # so try to get eventid  from plant name and date (pseudo-key) to avoid events being deleted
    # note: if we "replace" an event in the browser  (i.e. for a specific date, we delete an event and
    # create a new one, then that event in database will be modified, not deleted and re-created
    for event in [e for e in events if not e.id]:
        existing_event = await event_dal.get_event_by_plant_and_date(
            plant_obj, event.date
        )
        # event_obj_id = db.query(Event.id).filter(Event.plant_id == plant_obj.id,
        #                                          Event.date == event.date).scalar()
        if existing_event is not None:
            event.id = existing_event.id
            logger.info(
                f"Identified event without id from browser as id {event.id}"
            )  # todo remove??
    event_ids = [e.id for e in events]
    logger.info(f"Updating {len(events)} events ({event_ids})for plant {plant_id}")

    # loop at the current plant's database events to find deleted ones
    event_obj: Optional[Event]
    for event_obj in plant_obj.events:
        if event_obj.id not in event_ids:
            logger.info(f"Deleting event {event_obj.id}")
            if event_obj.image_to_event_associations:
                await event_dal.delete_image_to_event_associations(
                    event_obj.image_to_event_associations, event=event_obj
                )
            await event_dal.delete_event(event_obj)
            counts["Deleted Events"] += 1

    # loop at the current plant's events from frontend to find new events and modify existing ones
    for event in events:
        # new event
        if not event.id:
            # create event record
            logger.info("Creating event.")
            event_obj = Event(
                date=event.date, event_notes=event.event_notes, plant=plant_obj
            )
            await event_dal.create_event(event_obj)
            counts["Added Events"] += 1

            # as async does not allow for lazy loading, we need to reloda the event including
            # it's relationships
            event_obj = await event_dal.by_id(event_obj.id)

        # update existing event
        else:
            # try:
            logger.info(f"Getting event  {event.id}.")
            event_obj = await event_dal.by_id(event.id)
            if not event_obj:
                logger.warning(f"Event not found: {event.id}")
                continue
            event_obj.event_notes = event.event_notes
            event_obj.date = event.date

            # except InvalidRequestError as e:
            #     db.rollback()
            #     logger.error('Serious error occured at event resource (POST). Rollback. See log.',
            #                  stack_info=True, exc_info=e)
            #     throw_exception('Serious error occured at event resource (POST). Rollback. See log.')

        # segments observation, pot, and soil
        if event.observation and not event_obj.observation:
            observation_obj = Observation()
            await event_dal.create_observation(observation_obj)
            event_obj.observation = observation_obj
            counts["Added Observations"] += 1
        elif not event.observation and event_obj.observation:
            # 1:1 relationship, so we can delete the observation directly
            await event_dal.delete_observation(event_obj.observation)
            event_obj.observation = None
        if event.observation and event_obj.observation:
            event_obj.observation.diseases = event.observation.diseases
            event_obj.observation.observation_notes = (
                event.observation.observation_notes
            )
            event_obj.observation.height = event.observation.height
            event_obj.observation.stem_max_diameter = (
                event.observation.stem_max_diameter
            )
            # # cm to mm
            # event_obj.observation.height = event.observation.height * 10 if event.observation.height else None
            # event_obj.observation.stem_max_diameter = event.observation.stem_max_diameter * 10 if \
            #     event.observation.stem_max_diameter else None

        if not event.pot:
            # event_obj.pot_event_type = None
            event_obj.pot = None

        else:
            # event_obj.pot_event_type = event.pot_event_type
            # add empty if not existing
            if not event_obj.pot:
                pot_obj = Pot()
                await event_dal.create_pot(pot_obj)
                event_obj.pot = pot_obj
                counts["Added Pots"] += 1

            # pot objects have an id but are not "reused" for other events, so we may change it here
            event_obj.pot.material = event.pot.material
            event_obj.pot.shape_side = event.pot.shape_side
            event_obj.pot.shape_top = event.pot.shape_top
            event_obj.pot.diameter_width = event.pot.diameter_width
            # event_obj.pot.diameter_width = event.pot.diameter_width * 10 if event.pot.diameter_width else None

        # remove soil from event
        #  (event to soil is n:1 so we don't delete the soil object but only the assignment)
        if not event.soil:
            # event_obj.soil_event_type = None
            if event_obj.soil:
                event_obj.soil = None

        # add soil to event
        else:
            # event_obj.soil_event_type = event.soil_event_type
            if not event.soil.id:
                throw_exception(f"Can't update Soil {event.soil.soil_name} without ID.")
            if not event_obj.soil or (event.soil.id != event_obj.soil.id):
                soil = await event_dal.get_soil_by_id(event.soil.id)
                if not soil:
                    throw_exception(f"Soil ID {event.soil.id} not found")
                event_obj.soil = soil
                counts["Added Soils"] += 1

        # changes to images attached to the event
        # deleted images
        filenames_saved = (
            [image.filename for image in event.images] if event.images else []
        )
        for image_obj in event_obj.images:
            image_obj: Image
            if image_obj.filename not in filenames_saved:
                # don't delete photo_file object, but only the association
                # (photo_file might be assigned to other events)
                link: ImageToEventAssociation = next(
                    li
                    for li in event_obj.image_to_event_associations
                    if li.image.filename == image_obj.filename
                )
                await event_dal.delete_image_to_event_associations(links=[link])

        # newly assigned images
        if event.images:
            for image in event.images:
                image_obj = await image_dal.get_image_by_filename(image.filename)
                # image_obj = db.query(Image).filter(Image.relative_path == image.relative_path.as_posix()).scalar()
                # if not image_obj:
                #     raise ValueError(f'Image not in db: {image.relative_path.as_posix()}')

                # not assigned to that specific event, yet
                if image_obj not in event_obj.images:
                    event_obj.images.append(image_obj)


async def fetch_soils(plant_dal: PlantDAL, event_dal: EventDAL) -> list[Soil]:
    soils = []

    # add the number of plants that currently have a specific soil
    soil_counter = defaultdict(int)

    plants = await plant_dal.get_all_plants_with_events_loaded()
    for plant in plants:
        # if events := [e for e in plant.events if e.soil_id]:
        if events := [e for e in plant.events if e.soil and e.soil.id]:
            latest_event = max(events, key=attrgetter("date"))
            # soil_counter[latest_event.soil_id] += 1
            soil_counter[latest_event.soil.id] += 1

    all_soils = event_dal.get_all_soils()
    for soil in await all_soils:
        soil.plants_count = soil_counter.get(soil.id, 0)
        soils.append(soil)

    return soils
