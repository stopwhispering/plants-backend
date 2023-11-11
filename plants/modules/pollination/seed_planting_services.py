from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytz
from dateutil.relativedelta import relativedelta

from plants.exceptions import ValidationError
from plants.modules.event.models import Event
from plants.modules.plant.enums import FBPropagationType
from plants.modules.plant.schemas import PlantCreate, ShortPlant
from plants.modules.plant.services import create_new_plant
from plants.modules.pollination.enums import PollinationStatus, SeedPlantingStatus
from plants.modules.pollination.models import SeedPlanting
from plants.shared.api_constants import FORMAT_YYYY_MM_DD

if TYPE_CHECKING:
    from plants.modules.event.event_dal import EventDAL
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.pollination.pollination_dal import PollinationDAL
    from plants.modules.pollination.schemas import SeedPlantingCreate, SeedPlantingUpdate
    from plants.modules.pollination.seed_planting_dal import SeedPlantingDAL
    from plants.modules.taxon.taxon_dal import TaxonDAL


async def read_active_seed_plantings(
    seed_planting_dal: SeedPlantingDAL,
) -> list[SeedPlanting]:
    """Read all active seed plantings, i.e. seed plantings that have not been abandoned, yet, or
    that germinated not too long ago."""
    seed_plantings = await seed_planting_dal.by_status(
        {SeedPlantingStatus.PLANTED, SeedPlantingStatus.GERMINATED}
    )

    one_week_ago = (datetime.now(tz=pytz.utc) - relativedelta(days=7)).date()
    return [
        s
        for s in seed_plantings
        if s.status == SeedPlantingStatus.PLANTED
        or (s.status == SeedPlantingStatus.GERMINATED)
        and s.germinated_first_on is not None  # for mypy
        and s.germinated_first_on >= one_week_ago
    ]


async def save_new_seed_planting(
    new_seed_planting_data: SeedPlantingCreate,
    seed_planting_dal: SeedPlantingDAL,
) -> None:
    """Save a new seed planting."""
    new_seed_planting = SeedPlanting(
        status=SeedPlantingStatus.PLANTED,
        pollination_id=new_seed_planting_data.pollination_id,
        comment=new_seed_planting_data.comment,
        sterilized=new_seed_planting_data.sterilized,
        soaked=new_seed_planting_data.soaked,
        covered=new_seed_planting_data.covered,
        planted_on=new_seed_planting_data.planted_on,
        count_planted=new_seed_planting_data.count_planted,
        soil_id=new_seed_planting_data.soil_id,
    )
    await seed_planting_dal.create(new_seed_planting)


async def update_seed_planting(
    seed_planting: SeedPlanting,
    edited_seed_planting_data: SeedPlantingUpdate,
    seed_planting_dal: SeedPlantingDAL,
    pollination_dal: PollinationDAL,
) -> None:
    """Update db record of a seed planting."""
    if (
        edited_seed_planting_data.status == SeedPlantingStatus.GERMINATED
        and edited_seed_planting_data.germinated_first_on is None
    ):
        raise ValidationError("Germinated first on date must be set.")

    if (
        edited_seed_planting_data.status == SeedPlantingStatus.GERMINATED
        and not edited_seed_planting_data.count_germinated
    ):  # either zero or None
        raise ValidationError("Count germinated must be set.")

    if (
        edited_seed_planting_data.status == SeedPlantingStatus.ABANDONED
        and seed_planting.status != SeedPlantingStatus.ABANDONED
    ):
        edited_seed_planting_data.abandoned_on = datetime.now(tz=pytz.utc).date()

    if edited_seed_planting_data.status == SeedPlantingStatus.ABANDONED and (
        edited_seed_planting_data.germinated_first_on or edited_seed_planting_data.count_germinated
    ):
        raise ValidationError("Status Abandoned does not fit other parameters.")

    if edited_seed_planting_data.status == SeedPlantingStatus.PLANTED and (
        edited_seed_planting_data.germinated_first_on or edited_seed_planting_data.count_germinated
    ):
        raise ValidationError("Status Planted does not fit other parameters.")

    # set corresponding pollination to status GERMINATED if applicable
    if (
        edited_seed_planting_data.status == SeedPlantingStatus.GERMINATED
        and seed_planting.pollination.pollination_status != PollinationStatus.GERMINATED
    ):
        await pollination_dal.set_status(seed_planting.pollination, PollinationStatus.GERMINATED)

    updates = edited_seed_planting_data.dict(exclude={})
    await seed_planting_dal.update(seed_planting, updates=updates)


async def remove_seed_planting(
    seed_planting: SeedPlanting, seed_planting_dal: SeedPlantingDAL
) -> None:
    """Delete a seed planting from db."""
    await seed_planting_dal.delete(seed_planting)


async def create_new_plant_for_seed_planting(
    seed_planting: SeedPlanting,
    plant_name: str,
    plant_dal: PlantDAL,
    taxon_dal: TaxonDAL,
    event_dal: EventDAL,
) -> None:
    """Create a new plant for a seed planting."""
    if seed_planting.status != SeedPlantingStatus.GERMINATED:
        raise ValidationError("Seed planting must be germinated to create a new plant.")

    if seed_planting.germinated_first_on is None:
        raise ValidationError("Seed planting must have a germinated first on date.")

    plant_create = PlantCreate(
        plant_name=plant_name,
        field_number="-",
        geographic_origin="-",
        nursery_source="-",
        propagation_type=FBPropagationType.SEED_COLLECTED,
        active=True,
        generation_notes=f"auto-generated from Seed Planting ID {seed_planting.id}",
        # taxon_id=,
        parent_plant=ShortPlant.from_orm(seed_planting.pollination.seed_capsule_plant),
        parent_plant_pollen=ShortPlant.from_orm(seed_planting.pollination.pollen_donor_plant),
        # plant_notes=,
        # preview_image_id=,
        tags=[],
        seed_planting_id=seed_planting.id,
    )

    plant = await create_new_plant(new_plant=plant_create, plant_dal=plant_dal, taxon_dal=taxon_dal)

    notes = "Samen gesät"
    if seed_planting.sterilized:
        notes += "\nSamen zuvor gebeizt"
    if seed_planting.soaked:
        notes += "\nSamen zuvor eingeweicht"
    if seed_planting.covered:
        notes += "\nSamen abgedeckt"

    event_planted = Event(
        plant=plant,
        date=seed_planting.planted_on.strftime(FORMAT_YYYY_MM_DD),
        event_notes=notes,
        soil=seed_planting.soil,
    )

    event_germinated = Event(
        plant=plant,
        date=seed_planting.germinated_first_on.strftime(FORMAT_YYYY_MM_DD),
        event_notes="gekeimt",
        soil=seed_planting.soil,
    )
    await event_dal.create_events([event_planted, event_germinated])
