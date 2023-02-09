import datetime
from datetime import datetime
from typing import Final

from fastapi import HTTPException

from plants.exceptions import UnknownColor, ColorAlreadyTaken
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.pollination.florescence_dal import FlorescenceDAL
from plants.modules.pollination.models import (Florescence, Pollination)
from plants.modules.pollination.enums import PollinationStatus, PollenType, Context, Location, COLORS_MAP, \
    COLORS_MAP_TO_RGB, FlorescenceStatus
from plants.modules.pollination.ml_prediction import predict_probability_of_seed_production
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.shared.api_utils import format_api_date, format_api_datetime, parse_api_datetime, parse_api_date
from plants.shared.api_constants import FORMAT_FULL_DATETIME, FORMAT_YYYY_MM_DD, FORMAT_API_YYYY_MM_DD_HH_MM
from plants.modules.pollination.schemas import (PollinationCreate,
                                                BPotentialPollenDonor, BPollinationAttempt,
                                                BPollinationResultingPlant,
                                                BPlantWithoutPollenContainer,
                                                PollinationUpdate, PollinationRead, PollenContainerRead,
                                                PollenContainerCreateUpdate)  # noqa

LOCATION_TEXTS: Final[dict] = {
    'indoor': 'indoor',
    'outdoor': 'outdoor',
    'indoor_led': 'indoor LED',
    'unknown': 'unknown location',
}


async def _read_pollination_attempts(plant: Plant,
                                     pollen_donor: Plant,
                                     pollination_dal: PollinationDAL) -> list[BPollinationAttempt]:
    """ Read all pollination attempts for a plant and a pollen donor plus the other way around"""
    attempts_orm = await pollination_dal.get_pollinations_by_plants(plant, pollen_donor)
    # attempts_orm = db.query(Pollination).filter(Pollination.seed_capsule_plant_id == plant.id,
    #                                             Pollination.pollen_donor_plant_id == pollen_donor.id).all()
    attempts_orm_reverse = await pollination_dal.get_pollinations_by_plants(pollen_donor, plant)
    # attempts_orm_reverse = db.query(Pollination).filter(Pollination.seed_capsule_plant_id == pollen_donor.id,
    #                                                     Pollination.pollen_donor_plant_id == plant.id).all()
    attempts = []
    for pollination in (attempts_orm + attempts_orm_reverse):
        pollination: Pollination
        attempt_dict = {
            'reverse': True if pollination.seed_capsule_plant_id == pollen_donor.id else False,
            'pollination_status': pollination.pollination_status,
            'pollination_at': pollination.pollination_timestamp.strftime(FORMAT_FULL_DATETIME)
            if pollination.pollination_timestamp else None,
            'harvest_at': pollination.harvest_date.strftime(FORMAT_YYYY_MM_DD) if pollination.harvest_date else None,
            'germination_rate': pollination.germination_rate,
            'ongoing': pollination.ongoing,
        }
        attempts.append(BPollinationAttempt.parse_obj(attempt_dict))
    return attempts


async def _read_resulting_plants(plant: Plant,
                                 pollen_donor: Plant,
                                 plant_dal: PlantDAL) -> list[BPollinationResultingPlant]:
    resulting_plants_orm: list[Plant] = await plant_dal.get_children(plant, pollen_donor)
    # resulting_plants_orm = db.query(Plant).filter(Plant.parent_plant_id == plant.id,
    #                                               Plant.parent_plant_pollen_id == pollen_donor.id).all()
    resulting_plants_orm_reverse = await plant_dal.get_children(pollen_donor, plant)
    # resulting_plants_orm_reverse = db.query(Plant).filter(Plant.parent_plant_id == pollen_donor.id,
    #                                                       Plant.parent_plant_pollen_id == plant.id).all()
    resulting_plants = []
    for plant in (resulting_plants_orm + resulting_plants_orm_reverse):
        plant: Plant
        resulting_plant_dict = {
            'reverse': True if plant.parent_plant_id == pollen_donor.id else False,
            'plant_id': plant.id,
            'plant_name': plant.plant_name,
        }
        resulting_plants.append(BPollinationResultingPlant.parse_obj(resulting_plant_dict))
    return resulting_plants


def get_probability_pollination_to_seed(florescence: Florescence,
                                        pollen_donor: Plant,
                                        pollen_type: PollenType) -> int:
    """ Get the ml prediction for the probability of successful pollination to seed"""
    probability = predict_probability_of_seed_production(florescence=florescence,
                                                         pollen_donor=pollen_donor,
                                                         pollen_type=pollen_type)
    return probability


async def _plants_have_ongoing_pollination(seed_capsule_plant: Plant,
                                           pollen_donor_plant: Plant,
                                           pollination_dal: PollinationDAL) -> bool:
    ongoing_pollination = await pollination_dal.get_pollinations_with_filter({
        'ongoing': True,
        'seed_capsule_plant': seed_capsule_plant,
        'pollen_donor_plant': pollen_donor_plant,
    })
    return len(ongoing_pollination) > 0


async def read_potential_pollen_donors(florescence: Florescence,
                                       florescence_dal: FlorescenceDAL,
                                       pollination_dal: PollinationDAL,
                                       plant_dal: PlantDAL) -> list[BPotentialPollenDonor]:
    """ Read all potential pollen donors for a flowering plant; this can bei either another flowering
    plant or frozen pollen"""
    plant = await plant_dal.by_id(florescence.plant_id)
    potential_pollen_donors = []

    # 1. flowering plants
    # query = (db.query(Florescence)
    #          .filter(Florescence.florescence_status == FlorescenceStatus.FLOWERING,
    #                  # Florescence.plant_id != plant_id
    #                  ))
    # fresh_pollen_donors = query.all()
    fresh_pollen_donors: list[Florescence] = await florescence_dal.by_status([FlorescenceStatus.FLOWERING])
    for f in fresh_pollen_donors:
        already_ongoing_attempt = await _plants_have_ongoing_pollination(plant, f.plant, pollination_dal=pollination_dal)
        # already_ongoing_attempt = db.query(Pollination).filter(Pollination.ongoing,
        #                                                        Pollination.seed_capsule_plant == plant,
        #                                                        Pollination.pollen_donor_plant == f.plant).count() > 0
        potential_pollen_donor_flowering = {
            'plant_id': f.plant_id,
            'plant_name': f.plant.plant_name,
            'pollen_type': PollenType.FRESH.value,
            'count_stored_pollen_containers': None,
            'already_ongoing_attempt': already_ongoing_attempt,
            'probability_pollination_to_seed': get_probability_pollination_to_seed(florescence=florescence,
                                                                                   pollen_donor=f.plant,
                                                                                   pollen_type=PollenType.FRESH),
            'pollination_attempts': await _read_pollination_attempts(plant=plant,
                                                                     pollen_donor=f.plant,
                                                                     pollination_dal=pollination_dal),
            'resulting_plants': await _read_resulting_plants(plant=plant,
                                                             pollen_donor=f.plant,
                                                             plant_dal=plant_dal),
        }
        potential_pollen_donors.append(BPotentialPollenDonor.parse_obj(potential_pollen_donor_flowering))

    # 2. frozen pollen
    # query = (db.query(Plant).filter(  # Plant.florescence_status == FlorescenceStatus.FINISHED.value,
    #     Plant.id != florescence.plant_id,
    #     Plant.count_stored_pollen_containers >= 1))
    # frozen_pollen_plants = query.all()
    frozen_pollen_plants_ = await plant_dal.get_plants_with_pollen_containers()
    frozen_pollen_plants = [plant for plant in frozen_pollen_plants_ if plant.id != florescence.plant_id]

    for frozen_pollen_plant in frozen_pollen_plants:
        frozen_pollen_plant: Plant

        already_ongoing_attempt = await _plants_have_ongoing_pollination(plant, frozen_pollen_plant,
                                                                         pollination_dal=pollination_dal)

        # already_ongoing_attempt = db.query(Pollination).filter(
        #     Pollination.ongoing,
        #     Pollination.seed_capsule_plant == plant,
        potential_pollen_donor_frozen = {
            'plant_id': frozen_pollen_plant.id,
            'plant_name': frozen_pollen_plant.plant_name,
            'pollen_type': PollenType.FROZEN.value,
            'count_stored_pollen_containers': frozen_pollen_plant.count_stored_pollen_containers,
            'already_ongoing_attempt': already_ongoing_attempt,
            'probability_pollination_to_seed': get_probability_pollination_to_seed(florescence=florescence,
                                                                                   pollen_donor=frozen_pollen_plant,
                                                                                   pollen_type=PollenType.FROZEN),
            'pollination_attempts': await _read_pollination_attempts(plant=plant,
                                                                     pollen_donor=frozen_pollen_plant,
                                                                     pollination_dal=pollination_dal),
            'resulting_plants': await _read_resulting_plants(plant=plant,
                                                             pollen_donor=frozen_pollen_plant,
                                                             plant_dal=plant_dal),
        }
        #     Pollination.pollen_donor_plant == frozen_pollen_plant).count() > 0
        potential_pollen_donors.append(BPotentialPollenDonor.parse_obj(potential_pollen_donor_frozen))

    return potential_pollen_donors


async def save_new_pollination(new_pollination_data: PollinationCreate,
                               pollination_dal: PollinationDAL,
                               florescence_dal: FlorescenceDAL,
                               plant_dal: PlantDAL):
    """ Save a new pollination attempt """
    # validate data quality
    florescence = await florescence_dal.by_id(new_pollination_data.florescenceId)
    seed_capsule_plant = await plant_dal.by_id(new_pollination_data.seed_capsule_plant_id)
    pollen_donor_plant = await plant_dal.by_id(new_pollination_data.pollen_donor_plant_id)
    assert seed_capsule_plant is florescence.plant
    assert PollenType.has_value(new_pollination_data.pollen_type)
    assert Location.has_value(new_pollination_data.location)
    if new_pollination_data.label_color_rgb not in COLORS_MAP:
        raise UnknownColor(new_pollination_data.label_color_rgb)

    # apply transformations
    pollination_timestamp = datetime.strptime(new_pollination_data.pollination_timestamp, FORMAT_API_YYYY_MM_DD_HH_MM)

    # make sure there's no ongoing pollination for that plant with the same thread color
    label_color = COLORS_MAP[new_pollination_data.label_color_rgb]
    same_color_pollination = await pollination_dal.get_pollinations_with_filter({
        'seed_capsule_plant_id': new_pollination_data.seed_capsule_plant_id,
        'label_color': label_color,
    })
    if same_color_pollination:
        raise ColorAlreadyTaken(seed_capsule_plant.plant_name, label_color)

    # create new pollination orm object and write it to db
    pollination = Pollination(
        florescence_id=new_pollination_data.florescenceId,
        florescence=florescence,
        seed_capsule_plant_id=new_pollination_data.seed_capsule_plant_id,
        seed_capsule_plant=seed_capsule_plant,
        pollen_donor_plant_id=new_pollination_data.pollen_donor_plant_id,
        pollen_donor_plant=pollen_donor_plant,
        pollen_type=new_pollination_data.pollen_type,
        count=new_pollination_data.count,
        location=new_pollination_data.location,
        pollination_timestamp=pollination_timestamp,
        ongoing=True,
        label_color=COLORS_MAP[new_pollination_data.label_color_rgb],  # save the name of color, not the hex value
        pollination_status=PollinationStatus.ATTEMPT.value,  # noqa
        # creation_at=datetime.now(),
        creation_at_context=Context.API.value  # noqa
    )

    await pollination_dal.create(pollination)


async def remove_pollination(pollination: Pollination, pollination_dal: PollinationDAL):
    """ Delete a pollination attempt """
    await pollination_dal.delete(pollination)


async def update_pollination(pollination: Pollination,
                             pollination_data: PollinationUpdate,
                             pollination_dal: PollinationDAL):
    """ Update a pollination attempt """

    # technical validation (some values are not allowed to be changed)
    assert pollination is not None
    assert pollination.seed_capsule_plant_id == pollination_data.seed_capsule_plant_id
    assert pollination.pollen_donor_plant_id == pollination_data.pollen_donor_plant_id

    # semantic validation
    assert PollenType.has_value(pollination_data.pollen_type)
    assert Location.has_value(pollination_data.location)
    assert PollinationStatus.has_value(pollination_data.pollination_status)
    if pollination_data.label_color_rgb not in COLORS_MAP:
        raise HTTPException(500, detail={'message': f'Unknown color: {pollination_data.label_color_rgb}'})

    # transform rgb color to color name
    label_color = COLORS_MAP[pollination_data.label_color_rgb]

    # calculate and round germination rate (if applicable)
    if pollination_data.first_seeds_sown == 0:
        raise HTTPException(500, detail={'message': f'0 not allowed for "first seeds sown". Set empty instead.'})
    if pollination_data.first_seeds_sown is not None and pollination_data.first_seeds_germinated is not None:
        germination_rate = round(float(
            pollination_data.first_seeds_germinated * 100 / pollination_data.first_seeds_sown), 0)
    else:
        germination_rate = None

    updates = pollination_data.__dict__.copy()
    updates['pollination_timestamp'] = parse_api_datetime(pollination_data.pollination_timestamp)
    updates['labels_color'] = label_color
    updates['harvest_date'] = parse_api_date(pollination_data.harvest_date)
    updates['germination_rate'] = germination_rate
    updates['last_update_context'] = Context.API.value
    await pollination_dal.update(pollination, updates)

    # # update pollination orm object and write it to db
    # pollination.pollen_type = pollination_data.pollen_type
    # pollination.location = pollination_data.location
    # pollination.pollination_timestamp = parse_api_datetime(pollination_data.pollination_timestamp)
    # pollination.count = pollination_data.count
    # pollination.label_color = label_color
    # pollination.pollination_status = pollination_data.pollination_status
    # pollination.ongoing = pollination_data.ongoing
    # pollination.harvest_date = parse_api_date(pollination_data.harvest_date)
    # pollination.seed_capsule_length = pollination_data.seed_capsule_length
    # pollination.seed_capsule_width = pollination_data.seed_capsule_width
    # pollination.seed_length = pollination_data.seed_length
    # pollination.seed_width = pollination_data.seed_width
    # pollination.seed_count = pollination_data.seed_count
    # pollination.seed_capsule_description = pollination_data.seed_capsule_description
    # pollination.seed_description = pollination_data.seed_description
    # pollination.days_until_first_germination = pollination_data.days_until_first_germination
    # pollination.first_seeds_sown = pollination_data.first_seeds_sown
    # pollination.first_seeds_germinated = pollination_data.first_seeds_germinated
    # pollination.germination_rate = germination_rate
    #
    # # pollination.last_update_at = datetime.now()
    # pollination.last_update_context = Context.API.value


async def read_ongoing_pollinations(pollination_dal: PollinationDAL) -> list[PollinationRead]:
    # query = (db.query(Pollination)
    #          .filter(Pollination.ongoing)
    #          )
    # ongoing_pollinations_orm: list[Pollination] = query.all()
    ongoing_pollinations_orm: list[Pollination] = await pollination_dal.get_ongoing_pollinations()
    # todo pydantic orm mode
    ongoing_pollinations = []
    for p in ongoing_pollinations_orm:
        p: Pollination
        label_color_rgb = COLORS_MAP_TO_RGB.get(p.label_color, 'transparent')
        ongoing_pollination_dict = {
            'seed_capsule_plant_id': p.seed_capsule_plant_id,
            'seed_capsule_plant_name': p.seed_capsule_plant.plant_name,
            'pollen_donor_plant_id': p.pollen_donor_plant_id,
            'pollen_donor_plant_name': p.pollen_donor_plant.plant_name,
            'pollination_timestamp': format_api_datetime(p.pollination_timestamp),  # e.g. '2022-11-16 12:06'
            'pollen_type': p.pollen_type,
            'count': p.count,
            'location': p.location,
            'location_text': LOCATION_TEXTS[p.location],
            'label_color_rgb': label_color_rgb,

            'id': p.id,
            'pollination_status': p.pollination_status,
            'ongoing': p.ongoing,
            'harvest_date': format_api_date(p.harvest_date),  # e.g. '2022-11-16'
            'seed_capsule_length': p.seed_capsule_length,
            'seed_capsule_width': p.seed_capsule_width,
            'seed_length': p.seed_length,
            'seed_width': p.seed_width,
            'seed_count': p.seed_count,
            'seed_capsule_description': p.seed_capsule_description,
            'seed_description': p.seed_description,
            'days_until_first_germination': p.days_until_first_germination,
            'first_seeds_sown': p.first_seeds_sown,
            'first_seeds_germinated': p.first_seeds_germinated,
            'germination_rate': p.germination_rate,
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
        pollen_containers.append(PollenContainerRead(
            plant_id=p.id,
            plant_name=p.plant_name,
            genus=p.taxon.genus if p.taxon else None,
            count_stored_pollen_containers=p.count_stored_pollen_containers,
        ))

    return pollen_containers


async def read_plants_without_pollen_containers(plant_dal: PlantDAL) -> list[BPlantWithoutPollenContainer]:
    # query = (db.query(Plant).filter((Plant.count_stored_pollen_containers == 0) |
    #                                 Plant.count_stored_pollen_containers.is_(None))
    #          # .filter((Plant.hide.is_(False)) | (Plant.hide.is_(None))))
    #          .filter((Plant.deleted.is_(False))))
    # plants: list[Plant] = query.all()
    plants: list[Plant] = await plant_dal.get_plants_without_pollen_containers()

    plants_without_pollen_containers = []
    for p in plants:
        plants_without_pollen_containers.append(BPlantWithoutPollenContainer(
            plant_id=p.id,
            plant_name=p.plant_name,
            genus=p.taxon.genus if p.taxon else None,
        ))
    return plants_without_pollen_containers


async def update_pollen_containers(pollen_containers_data: list[PollenContainerCreateUpdate], plant_dal: PlantDAL):
    for pollen_container_data in pollen_containers_data:
        # plant = Plant.by_id(pollen_container_data.plant_id, db)
        # plant.count_stored_pollen_containers = pollen_container_data.count_stored_pollen_containers
        plant = await plant_dal.by_id(pollen_container_data.plant_id)
        await plant_dal.set_count_stored_pollen_containers(plant, pollen_container_data.count_stored_pollen_containers)
