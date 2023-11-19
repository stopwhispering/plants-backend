from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import pytz
from fastapi import HTTPException

from plants.exceptions import BaseError, ColorAlreadyTakenError, UnknownColorError
from plants.modules.pollination.enums import (
    COLORS_MAP,
    Context,
    FlorescenceStatus,
    PollenType,
    PollinationStatus,
)
from plants.modules.pollination.models import Florescence, Pollination
from plants.modules.pollination.prediction.predict_pollination import (
    predict_probability_of_seed_production,
)
from plants.modules.pollination.prediction.predict_ripening import predict_ripening_days
from plants.modules.pollination.schemas import (
    BPlantWoPollenContainer,
    BPotentialPollenDonor,
    HistoricalPollinationRead,
    PollenContainerCreateUpdate,
    PollenContainerRead,
    PollinationCreate,
    PollinationUpdate,
)
from plants.shared.api_constants import (
    FORMAT_API_YYYY_MM_DD_HH_MM,
)
from plants.shared.api_utils import (
    parse_api_date,
    parse_api_datetime,
)

if TYPE_CHECKING:
    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.pollination.florescence_dal import FlorescenceDAL
    from plants.modules.pollination.pollination_dal import PollinationDAL

logger = logging.getLogger(__name__)


async def _read_pollination_attempts(
    plant_id: int, pollen_donor_id: int, pollination_dal: PollinationDAL
) -> list[HistoricalPollinationRead]:
    """Read all pollination attempts for a plant and a pollen donor plus the other way around."""
    attempts_orm = await pollination_dal.get_pollinations_by_plants(
        seed_capsule_plant_id=plant_id, pollen_donor_plant_id=pollen_donor_id
    )
    attempts_orm_reverse = await pollination_dal.get_pollinations_by_plants(
        seed_capsule_plant_id=pollen_donor_id, pollen_donor_plant_id=plant_id
    )

    attempts = []
    for p in attempts_orm + attempts_orm_reverse:
        pollination = HistoricalPollinationRead.model_validate(p, context={"reverse": True})
        pollination.reverse = pollination.seed_capsule_plant_id == pollen_donor_id
        # todo predict?
        attempts.append(pollination)

    return attempts


def get_probability_pollination_to_seed(
    florescence: Florescence, pollen_donor: Plant, pollen_type: PollenType
) -> int:
    """Get the ml prediction for the probability of successful pollination to seed."""
    return predict_probability_of_seed_production(
        florescence=florescence, pollen_donor=pollen_donor, pollen_type=pollen_type
    )


async def _plants_have_ongoing_pollination(
    seed_capsule_plant_id: int,
    pollen_donor_plant_id: int,
    pollination_dal: PollinationDAL,
) -> bool:
    ongoing_pollination = await pollination_dal.get_pollinations_with_filter(
        {
            "ongoing": True,
            "seed_capsule_plant_id": seed_capsule_plant_id,
            "pollen_donor_plant_id": pollen_donor_plant_id,
        }
    )
    return len(ongoing_pollination) > 0


async def read_potential_pollen_donors(
    florescence: Florescence,
    florescence_dal: FlorescenceDAL,
    pollination_dal: PollinationDAL,
    plant_dal: PlantDAL,
) -> list[BPotentialPollenDonor]:
    """Read all potential pollen donors for a flowering plant; this can bei either another flowering
    plant or frozen pollen."""

    potential_pollen_donors: list[BPotentialPollenDonor] = []

    # 1. flowering plants
    fresh_pollen_donors: list[Florescence] = await florescence_dal.by_status(
        [FlorescenceStatus.FLOWERING]
    )

    for florescence_pollen_donor in fresh_pollen_donors:
        if florescence_pollen_donor is florescence:
            continue

        # also skip other active florescences of our plant
        if florescence_pollen_donor.plant_id == florescence.plant_id:
            continue

        # if plant has multiple active florescences, return only the first one
        if any(
            p
            for p in potential_pollen_donors
            if p.plant_id == florescence_pollen_donor.plant_id and p.pollen_type == PollenType.FRESH
        ):
            continue

        already_ongoing_attempt = await _plants_have_ongoing_pollination(
            seed_capsule_plant_id=florescence.plant_id,
            pollen_donor_plant_id=florescence_pollen_donor.plant_id,
            pollination_dal=pollination_dal,
        )
        potential_pollen_donor_flowering = {
            "plant_id": florescence_pollen_donor.plant_id,
            "plant_name": florescence_pollen_donor.plant.plant_name,
            "plant_preview_image_id": florescence_pollen_donor.plant.preview_image_id,
            "pollen_type": PollenType.FRESH.value,
            "count_stored_pollen_containers": None,
            "already_ongoing_attempt": already_ongoing_attempt,
            "probability_pollination_to_seed": get_probability_pollination_to_seed(
                florescence=florescence,
                pollen_donor=florescence_pollen_donor.plant,
                pollen_type=PollenType.FRESH,
            )
            if florescence_pollen_donor.plant.taxon and florescence.plant.taxon
            else None,
            "pollination_attempts": await _read_pollination_attempts(
                plant_id=florescence.plant_id,
                pollen_donor_id=florescence_pollen_donor.plant.id,
                pollination_dal=pollination_dal,
            ),
        }
        potential_pollen_donors.append(
            BPotentialPollenDonor.model_validate(potential_pollen_donor_flowering)
        )

    # 2. frozen pollen
    frozen_pollen_plants_ = await plant_dal.get_plants_with_pollen_containers()
    frozen_pollen_plants = [p for p in frozen_pollen_plants_ if p.id != florescence.plant_id]

    frozen_pollen_plant: Plant
    for frozen_pollen_plant in frozen_pollen_plants:
        if frozen_pollen_plant.id == florescence.plant_id:
            continue

        already_ongoing_attempt = await _plants_have_ongoing_pollination(
            seed_capsule_plant_id=florescence.plant_id,
            pollen_donor_plant_id=frozen_pollen_plant.id,
            pollination_dal=pollination_dal,
        )

        potential_pollen_donor_frozen = {
            "plant_id": frozen_pollen_plant.id,
            "plant_name": frozen_pollen_plant.plant_name,
            "plant_preview_image_id": frozen_pollen_plant.preview_image_id,
            "pollen_type": PollenType.FROZEN.value,
            "count_stored_pollen_containers": frozen_pollen_plant.count_stored_pollen_containers,
            "already_ongoing_attempt": already_ongoing_attempt,
            "probability_pollination_to_seed": get_probability_pollination_to_seed(
                florescence=florescence,
                pollen_donor=frozen_pollen_plant,
                pollen_type=PollenType.FROZEN,
            )
            if frozen_pollen_plant.taxon and florescence.plant.taxon
            else None,
            "pollination_attempts": await _read_pollination_attempts(
                plant_id=florescence.plant_id,
                pollen_donor_id=frozen_pollen_plant.id,
                pollination_dal=pollination_dal,
            ),
        }
        potential_pollen_donors.append(
            BPotentialPollenDonor.model_validate(potential_pollen_donor_frozen)
        )

    return potential_pollen_donors


async def save_new_pollination(
    new_pollination_data: PollinationCreate,
    pollination_dal: PollinationDAL,
    florescence_dal: FlorescenceDAL,
    plant_dal: PlantDAL,
) -> None:
    """Save a new pollination attempt."""
    # validate data quality
    florescence = await florescence_dal.by_id(new_pollination_data.florescence_id)
    seed_capsule_plant = await plant_dal.by_id(new_pollination_data.seed_capsule_plant_id)
    if florescence.plant_id != seed_capsule_plant.id:
        raise BaseError("Plant ID mismatch")

    pollen_donor_plant = await plant_dal.by_id(new_pollination_data.pollen_donor_plant_id)

    if new_pollination_data.label_color_rgb not in COLORS_MAP:
        raise UnknownColorError(new_pollination_data.label_color_rgb)

    # apply transformations
    # we have datetime as a string, we can assume it relates to Europe/Berlin timezone
    # to get a DateTime object with UTC timezone attached, we need to...
    # 1. parse the string to a timezone-naive datetime object
    # 2. attach the timezone with pytz localize
    # 3. convert to UTC with astimezone
    pollinated_at_ = new_pollination_data.pollinated_at or "1900-01-01"  # legacy data
    pollinated_at_naive = datetime.strptime(  # noqa: DTZ007
        pollinated_at_, FORMAT_API_YYYY_MM_DD_HH_MM
    )
    pollinated_at_localized = pytz.timezone("Europe/Berlin").localize(pollinated_at_naive)
    pollinated_at = pollinated_at_localized.astimezone(pytz.utc)

    # make sure there's no ongoing pollination for that plant with the same thread color
    label_color = COLORS_MAP[new_pollination_data.label_color_rgb]
    same_color_pollination = await pollination_dal.get_pollinations_with_filter(
        {
            # "seed_capsule_plant_id": new_pollination_data.seed_capsule_plant_id,
            "florescence_id": new_pollination_data.florescence_id,
            "label_color": label_color,
            "ongoing": True,
        }
    )
    if same_color_pollination:
        raise ColorAlreadyTakenError(seed_capsule_plant.plant_name, label_color)

    # create new pollination orm object and write it to db
    pollination = Pollination(
        florescence_id=new_pollination_data.florescence_id,
        florescence=florescence,
        seed_capsule_plant_id=new_pollination_data.seed_capsule_plant_id,
        seed_capsule_plant=seed_capsule_plant,
        pollen_donor_plant_id=new_pollination_data.pollen_donor_plant_id,
        pollen_donor_plant=pollen_donor_plant,
        pollen_type=new_pollination_data.pollen_type,
        pollen_quality=new_pollination_data.pollen_quality,
        count_attempted=new_pollination_data.count_attempted,
        location=new_pollination_data.location,
        pollinated_at=pollinated_at,
        ongoing=True,
        label_color=COLORS_MAP[
            new_pollination_data.label_color_rgb
        ],  # save the name of color, not the hex value
        pollination_status=PollinationStatus.ATTEMPT,
        creation_at_context=Context.API,
    )

    await pollination_dal.create(pollination)


async def remove_pollination(pollination: Pollination, pollination_dal: PollinationDAL) -> None:
    """Delete a pollination attempt."""
    await pollination_dal.delete(pollination)


async def update_pollination(
    pollination: Pollination,
    pollination_data: PollinationUpdate,
    pollination_dal: PollinationDAL,
) -> None:
    """Update a pollination attempt."""
    # technical validation (some values are not allowed to be changed)
    if (
        pollination.seed_capsule_plant_id != pollination_data.seed_capsule_plant_id
        or pollination.pollen_donor_plant_id != pollination_data.pollen_donor_plant_id
    ):
        raise HTTPException(
            400,
            detail={"message": "Seed capsule plant and pollen donor plant cannot be " "changed."},
        )

    # semantic validation
    if pollination_data.label_color_rgb not in COLORS_MAP:
        raise HTTPException(
            500,
            detail={"message": f"Unknown color: {pollination_data.label_color_rgb}"},
        )

    # transform rgb color to color name
    label_color = COLORS_MAP[pollination_data.label_color_rgb]

    updates = pollination_data.model_dump(exclude={})
    pollinated_at_ = pollination_data.pollinated_at or "1900-01-01"  # legacy data
    updates["pollinated_at"] = parse_api_datetime(pollinated_at_)
    updates["label_color"] = label_color
    updates["harvest_date"] = parse_api_date(pollination_data.harvest_date)
    updates["last_update_context"] = Context.API
    await pollination_dal.update(pollination, updates)


def get_predicted_ripening_days(pollination: Pollination) -> int | None:
    """Predict the ripening days of a pollination attempt."""
    return predict_ripening_days(pollination=pollination)


async def read_pollinations(
    pollination_dal: PollinationDAL,
    *,
    include_ongoing_pollinations: bool,
    include_finished_pollinations: bool,
) -> list[Pollination]:
    pollinations_orm: list[Pollination] = await pollination_dal.get_pollinations(
        include_ongoing_pollinations=include_ongoing_pollinations,
        include_finished_pollinations=include_finished_pollinations,
    )
    return pollinations_orm


async def read_pollen_containers(plant_dal: PlantDAL) -> list[PollenContainerRead]:
    plants: list[Plant] = await plant_dal.get_plants_with_pollen_containers()

    pollen_containers = []
    for plant in plants:
        pollen_containers.append(
            PollenContainerRead(
                plant_id=plant.id,
                plant_name=plant.plant_name,
                genus=plant.taxon.genus if plant.taxon else None,
                count_stored_pollen_containers=plant.count_stored_pollen_containers
                if plant.count_stored_pollen_containers
                else 0,
            )
        )

    return pollen_containers


async def read_plants_without_pollen_containers(
    plant_dal: PlantDAL,
) -> list[BPlantWoPollenContainer]:
    # query = (db.query(Plant).filter((Plant.count_stored_pollen_containers == 0) |
    #                                 Plant.count_stored_pollen_containers.is_(None))
    #          # .filter((Plant.hide.is_(False)) | (Plant.hide.is_(None))))
    #          .filter((Plant.deleted.is_(False))))
    # plants: list[Plant] = query.all()
    plants: list[Plant] = await plant_dal.get_plants_without_pollen_containers()

    plants_without_pollen_containers = []
    for plant in plants:
        plants_without_pollen_containers.append(
            BPlantWoPollenContainer(
                plant_id=plant.id,
                plant_name=plant.plant_name,
                genus=plant.taxon.genus if plant.taxon else None,
            )
        )
    return plants_without_pollen_containers


async def update_pollen_containers(
    pollen_containers_data: list[PollenContainerCreateUpdate], plant_dal: PlantDAL
) -> None:
    for pollen_container_data in pollen_containers_data:
        plant = await plant_dal.by_id(pollen_container_data.plant_id)
        await plant_dal.set_count_stored_pollen_containers(
            plant, pollen_container_data.count_stored_pollen_containers
        )
