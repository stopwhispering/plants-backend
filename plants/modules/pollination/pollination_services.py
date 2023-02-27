from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Final

from fastapi import HTTPException

from plants.exceptions import ColorAlreadyTakenError, UnknownColorError
from plants.modules.pollination.enums import (
    COLORS_MAP,
    COLORS_MAP_TO_RGB,
    Context,
    FlorescenceStatus,
    Location,
    PollenType,
    PollinationStatus,
)
from plants.modules.pollination.ml_prediction import (
    predict_probability_of_seed_production,
)
from plants.modules.pollination.models import Florescence, Pollination
from plants.modules.pollination.schemas import PollenContainerCreateUpdate  # noqa
from plants.modules.pollination.schemas import (
    BPlantWoPollenContainer,
    BPollinationAttempt,
    BPollinationResultingPlant,
    BPotentialPollenDonor,
    PollenContainerRead,
    PollinationCreate,
    PollinationRead,
    PollinationUpdate,
)
from plants.shared.api_constants import (
    FORMAT_API_YYYY_MM_DD_HH_MM,
    FORMAT_FULL_DATETIME,
    FORMAT_YYYY_MM_DD,
)
from plants.shared.api_utils import (
    format_api_date,
    format_api_datetime,
    parse_api_date,
    parse_api_datetime,
)

if TYPE_CHECKING:
    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.pollination.florescence_dal import FlorescenceDAL
    from plants.modules.pollination.pollination_dal import PollinationDAL

LOCATION_TEXTS: Final[dict[str, str]] = {
    "indoor": "indoor",
    "outdoor": "outdoor",
    "indoor_led": "indoor LED",
    "unknown": "unknown location",
}


async def _read_pollination_attempts(
    plant: Plant, pollen_donor: Plant, pollination_dal: PollinationDAL
) -> list[BPollinationAttempt]:
    """Read all pollination attempts for a plant and a pollen donor plus the other way
    around."""
    attempts_orm = await pollination_dal.get_pollinations_by_plants(plant, pollen_donor)
    attempts_orm_reverse = await pollination_dal.get_pollinations_by_plants(
        pollen_donor, plant
    )
    attempts = []
    pollination: Pollination
    for pollination in attempts_orm + attempts_orm_reverse:
        attempt_dict = {
            "reverse": pollination.seed_capsule_plant_id == pollen_donor.id,
            "pollination_status": pollination.pollination_status,
            "pollination_at": pollination.pollination_timestamp.strftime(
                FORMAT_FULL_DATETIME
            )
            if pollination.pollination_timestamp
            else None,
            "harvest_at": pollination.harvest_date.strftime(FORMAT_YYYY_MM_DD)
            if pollination.harvest_date
            else None,
            "germination_rate": pollination.germination_rate,
            "ongoing": pollination.ongoing,
        }
        attempts.append(BPollinationAttempt.parse_obj(attempt_dict))
    return attempts


async def _read_resulting_plants(
    plant: Plant, pollen_donor: Plant, plant_dal: PlantDAL
) -> list[BPollinationResultingPlant]:
    resulting_plants_orm: list[Plant] = await plant_dal.get_children(
        plant, pollen_donor
    )
    resulting_plants_orm_reverse = await plant_dal.get_children(pollen_donor, plant)
    resulting_plants = []
    for plant in resulting_plants_orm + resulting_plants_orm_reverse:
        resulting_plant_dict = {
            "reverse": plant.parent_plant_id == pollen_donor.id,
            "plant_id": plant.id,
            "plant_name": plant.plant_name,
        }
        resulting_plants.append(
            BPollinationResultingPlant.parse_obj(resulting_plant_dict)
        )
    return resulting_plants


def get_probability_pollination_to_seed(
    florescence: Florescence, pollen_donor: Plant, pollen_type: PollenType
) -> int:
    """Get the ml prediction for the probability of successful pollination to seed."""
    return predict_probability_of_seed_production(
        florescence=florescence, pollen_donor=pollen_donor, pollen_type=pollen_type
    )


async def _plants_have_ongoing_pollination(
    seed_capsule_plant: Plant,
    pollen_donor_plant: Plant,
    pollination_dal: PollinationDAL,
) -> bool:
    ongoing_pollination = await pollination_dal.get_pollinations_with_filter(
        {
            "ongoing": True,
            "seed_capsule_plant": seed_capsule_plant,
            "pollen_donor_plant": pollen_donor_plant,
        }
    )
    return len(ongoing_pollination) > 0


async def read_potential_pollen_donors(
    florescence: Florescence,
    florescence_dal: FlorescenceDAL,
    pollination_dal: PollinationDAL,
    plant_dal: PlantDAL,
) -> list[BPotentialPollenDonor]:
    """Read all potential pollen donors for a flowering plant; this can bei either
    another flowering plant or frozen pollen."""
    plant = await plant_dal.by_id(florescence.plant_id)
    potential_pollen_donors = []

    # 1. flowering plants
    # query = (db.query(Florescence)
    #          .filter(Florescence.florescence_status == FlorescenceStatus.FLOWERING,
    #                  # Florescence.plant_id != plant_id
    #                  ))
    # fresh_pollen_donors = query.all()
    fresh_pollen_donors: list[Florescence] = await florescence_dal.by_status(
        [FlorescenceStatus.FLOWERING]
    )
    for f in fresh_pollen_donors:
        if f is florescence:
            continue
        already_ongoing_attempt = await _plants_have_ongoing_pollination(
            plant, f.plant, pollination_dal=pollination_dal
        )
        potential_pollen_donor_flowering = {
            "plant_id": f.plant_id,
            "plant_name": f.plant.plant_name,
            "pollen_type": PollenType.FRESH.value,
            "count_stored_pollen_containers": None,
            "already_ongoing_attempt": already_ongoing_attempt,
            "probability_pollination_to_seed": get_probability_pollination_to_seed(
                florescence=florescence,
                pollen_donor=f.plant,
                pollen_type=PollenType.FRESH,
            ),
            "pollination_attempts": await _read_pollination_attempts(
                plant=plant, pollen_donor=f.plant, pollination_dal=pollination_dal
            ),
            "resulting_plants": await _read_resulting_plants(
                plant=plant, pollen_donor=f.plant, plant_dal=plant_dal
            ),
        }
        potential_pollen_donors.append(
            BPotentialPollenDonor.parse_obj(potential_pollen_donor_flowering)
        )

    # 2. frozen pollen
    frozen_pollen_plants_ = await plant_dal.get_plants_with_pollen_containers()
    frozen_pollen_plants = [
        plant for plant in frozen_pollen_plants_ if plant.id != florescence.plant_id
    ]

    frozen_pollen_plant: Plant
    for frozen_pollen_plant in frozen_pollen_plants:
        if frozen_pollen_plant.id == florescence.plant_id:
            continue

        already_ongoing_attempt = await _plants_have_ongoing_pollination(
            plant, frozen_pollen_plant, pollination_dal=pollination_dal
        )

        potential_pollen_donor_frozen = {
            "plant_id": frozen_pollen_plant.id,
            "plant_name": frozen_pollen_plant.plant_name,
            "pollen_type": PollenType.FROZEN.value,
            "count_stored_pollen_containers": (
                frozen_pollen_plant.count_stored_pollen_containers
            ),
            "already_ongoing_attempt": already_ongoing_attempt,
            "probability_pollination_to_seed": get_probability_pollination_to_seed(
                florescence=florescence,
                pollen_donor=frozen_pollen_plant,
                pollen_type=PollenType.FROZEN,
            ),
            "pollination_attempts": await _read_pollination_attempts(
                plant=plant,
                pollen_donor=frozen_pollen_plant,
                pollination_dal=pollination_dal,
            ),
            "resulting_plants": await _read_resulting_plants(
                plant=plant, pollen_donor=frozen_pollen_plant, plant_dal=plant_dal
            ),
        }
        #     Pollination.pollen_donor_plant == frozen_pollen_plant).count() > 0
        potential_pollen_donors.append(
            BPotentialPollenDonor.parse_obj(potential_pollen_donor_frozen)
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
    florescence = await florescence_dal.by_id(new_pollination_data.florescenceId)
    seed_capsule_plant = await plant_dal.by_id(
        new_pollination_data.seed_capsule_plant_id
    )
    pollen_donor_plant = await plant_dal.by_id(
        new_pollination_data.pollen_donor_plant_id
    )
    if not (
        seed_capsule_plant is florescence.plant
        and PollenType.has_value(new_pollination_data.pollen_type)
        and Location.has_value(new_pollination_data.location)
    ):
        raise ValueError("Invalid pollination data")
    if new_pollination_data.label_color_rgb not in COLORS_MAP:
        raise UnknownColorError(new_pollination_data.label_color_rgb)

    # apply transformations
    pollination_timestamp = datetime.strptime(
        new_pollination_data.pollination_timestamp, FORMAT_API_YYYY_MM_DD_HH_MM
    )

    # make sure there's no ongoing pollination for that plant with the same thread color
    label_color = COLORS_MAP[new_pollination_data.label_color_rgb]
    same_color_pollination = await pollination_dal.get_pollinations_with_filter(
        {
            "seed_capsule_plant_id": new_pollination_data.seed_capsule_plant_id,
            "label_color": label_color,
        }
    )
    if same_color_pollination:
        raise ColorAlreadyTakenError(seed_capsule_plant.plant_name, label_color)

    # create new pollination orm object and write it to db
    pollination = Pollination(
        florescence_id=new_pollination_data.florescenceId,
        florescence=florescence,
        seed_capsule_plant_id=new_pollination_data.seed_capsule_plant_id,
        seed_capsule_plant=seed_capsule_plant,
        pollen_donor_plant_id=new_pollination_data.pollen_donor_plant_id,
        pollen_donor_plant=pollen_donor_plant,
        pollen_type=new_pollination_data.pollen_type,
        pollen_quality=new_pollination_data.pollen_quality,
        count=new_pollination_data.count,
        location=new_pollination_data.location,
        pollination_timestamp=pollination_timestamp,
        ongoing=True,
        label_color=COLORS_MAP[
            new_pollination_data.label_color_rgb
        ],  # save the name of color, not the hex value
        pollination_status=PollinationStatus.ATTEMPT.value,  # noqa
        # creation_at=datetime.now(),
        creation_at_context=Context.API.value,  # noqa
    )

    await pollination_dal.create(pollination)


async def remove_pollination(
    pollination: Pollination, pollination_dal: PollinationDAL
) -> None:
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
            detail={
                "message": "Seed capsule plant and pollen donor plant cannot be changed."
            },
        )

    # semantic validation
    if not (
        PollenType.has_value(pollination_data.pollen_type)
        and Location.has_value(pollination_data.location)
        and PollinationStatus.has_value(pollination_data.pollination_status)
    ):
        raise HTTPException(
            400,
            detail={"message": "Invalid value for pollination data."},
        )
    if pollination_data.label_color_rgb not in COLORS_MAP:
        raise HTTPException(
            500,
            detail={"message": f"Unknown color: {pollination_data.label_color_rgb}"},
        )

    # transform rgb color to color name
    label_color = COLORS_MAP[pollination_data.label_color_rgb]

    # calculate and round germination rate (if applicable)
    if pollination_data.first_seeds_sown == 0:
        raise HTTPException(
            500,
            detail={
                "message": '0 not allowed for "first seeds sown". Set empty instead.'
            },
        )
    if (
        pollination_data.first_seeds_sown is not None
        and pollination_data.first_seeds_germinated is not None
    ):
        germination_rate = round(
            float(
                pollination_data.first_seeds_germinated
                * 100
                / pollination_data.first_seeds_sown
            ),
            0,
        )
    else:
        germination_rate = None

    updates = pollination_data.dict(exclude={})
    updates["pollination_timestamp"] = parse_api_datetime(
        pollination_data.pollination_timestamp
    )
    updates["label_color"] = label_color
    updates["harvest_date"] = parse_api_date(pollination_data.harvest_date)
    updates["germination_rate"] = germination_rate
    updates["last_update_context"] = Context.API.value
    await pollination_dal.update(pollination, updates)


async def read_ongoing_pollinations(
    pollination_dal: PollinationDAL,
) -> list[PollinationRead]:
    # query = (db.query(Pollination)
    #          .filter(Pollination.ongoing)
    #          )
    # ongoing_pollinations_orm: list[Pollination] = query.all()
    ongoing_pollinations_orm: list[
        Pollination
    ] = await pollination_dal.get_ongoing_pollinations()
    # todo pydantic orm mode
    ongoing_pollinations = []
    p: Pollination
    for p in ongoing_pollinations_orm:
        label_color_rgb = (
            COLORS_MAP_TO_RGB.get(p.label_color, "transparent")
            if p.label_color
            else None
        )
        ongoing_pollination_dict = {
            "seed_capsule_plant_id": p.seed_capsule_plant_id,
            "seed_capsule_plant_name": p.seed_capsule_plant.plant_name,
            "pollen_donor_plant_id": p.pollen_donor_plant_id,
            "pollen_donor_plant_name": p.pollen_donor_plant.plant_name,
            "pollination_timestamp": format_api_datetime(
                p.pollination_timestamp
            ),  # e.g. '2022-11-16 12:06'
            "pollen_type": p.pollen_type,
            "count": p.count,
            "pollen_quality": p.pollen_quality,
            "location": p.location,
            "location_text": LOCATION_TEXTS[p.location],
            "label_color_rgb": label_color_rgb,
            "id": p.id,
            "pollination_status": p.pollination_status,
            "ongoing": p.ongoing,
            "harvest_date": format_api_date(p.harvest_date),  # e.g. '2022-11-16'
            "seed_capsule_length": p.seed_capsule_length,
            "seed_capsule_width": p.seed_capsule_width,
            "seed_length": p.seed_length,
            "seed_width": p.seed_width,
            "seed_count": p.seed_count,
            "seed_capsule_description": p.seed_capsule_description,
            "seed_description": p.seed_description,
            "days_until_first_germination": p.days_until_first_germination,
            "first_seeds_sown": p.first_seeds_sown,
            "first_seeds_germinated": p.first_seeds_germinated,
            "germination_rate": p.germination_rate,
        }
        # POngoingPollination.validate(ongoing_pollination_dict)
        ongoing_pollinations.append(PollinationRead.parse_obj(ongoing_pollination_dict))
    return ongoing_pollinations


async def read_pollen_containers(plant_dal: PlantDAL) -> list[PollenContainerRead]:
    # query = db.query(Plant).filter(Plant.count_stored_pollen_containers >= 1)
    # plants: list[Plant] = query.all()
    plants: list[Plant] = await plant_dal.get_plants_with_pollen_containers()

    pollen_containers = []
    for p in plants:
        pollen_containers.append(
            PollenContainerRead(
                plant_id=p.id,
                plant_name=p.plant_name,
                genus=p.taxon.genus if p.taxon else None,
                count_stored_pollen_containers=p.count_stored_pollen_containers,
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
    for p in plants:
        plants_without_pollen_containers.append(
            BPlantWoPollenContainer(
                plant_id=p.id,
                plant_name=p.plant_name,
                genus=p.taxon.genus if p.taxon else None,
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
