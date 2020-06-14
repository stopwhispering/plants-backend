import datetime
import logging
from typing import List

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.plant_models import Plant
from plants_tagger.models.tag_models import Tag
from plants_tagger.services.tag_services import tag_modified, update_tag

logger = logging.getLogger(__name__)


def update_plants_from_list_of_dicts(plants: [dict]):

    new_list = []
    logger.info(f"Updating/Creating {len(plants)} plants")
    for plant in plants:
        record_update = Plant.get_plant_by_plant_name(plant['plant_name'])

        if boo_new := False if record_update else True:
            if [r for r in new_list if r.plant_name == plant['plant_name']]:
                continue  # same plant in multiple new records
            # create new record (as object) & add to list later)
            record_update = Plant(plant_name=plant['plant_name'])
            logger.info(f'Saving new plant {plant["plant_name"]}')

        # catch key errors (new entries don't have all keys in the dict)
        record_update.plant_name = plant['plant_name']   # key is always supplied
        record_update.active = plant['active'] if 'active' in plant else None

        record_update.set_count(plant=plant)
        record_update.set_field_number(plant=plant)
        record_update.set_geographic_origin(plant=plant)
        record_update.set_nursery_source(plant=plant)
        record_update.set_propagation_type(plant=plant)

        record_update.set_generation_date(plant=plant)
        record_update.set_generation_type(plant=plant)
        record_update.set_generation_notes(plant=plant)
        record_update.set_generation_origin(plant=plant)
        record_update.set_plant_notes(plant=plant)

        # mother_plant_id is still the old one if changed; but mother_plant the new mother plant
        # in db, we only persist the mother plant id
        record_update.set_mother_plant(mother_plant_name=plant.get('mother_plant'))
        record_update.set_filename_previewimage(plant=plant)
        record_update.set_taxon(plant=plant)
        record_update.set_last_update()

        # create new, update existing and remove deleted tags
        new_tags = _update_tags(record_update, plant.get('tags'))
        new_list.extend(new_tags)

        if boo_new:
            new_list.append(record_update)

    if new_list:
        get_sql_session().add_all(new_list)

    get_sql_session().commit()  # saves changes in existing records, too


def _update_tags(plant_obj: Plant, tags: List[dict]):
    """update modified tags; returns list of new tags (not yet added or committed); removes deleted tags"""
    new_list = []
    if tags:
        for tag in tags:
            if 'id' not in tag:
                # new tag
                tag_object: Tag = Tag(text=tag['text'],
                                      icon=tag['icon'],
                                      state=tag['state'],
                                      plant=plant_obj,
                                      last_update=datetime.datetime.now())
                new_list.append(tag_object)
            else:
                # update if modified (not implemented in frontend)
                tag_object = Tag.get_tag_by_tag_id(tag['id'], raise_exception=True)
                if tag_modified(tag_object, tag):
                    update_tag(tag_object, tag)

    # query raises exception for new plant objects that have no id, yet
    # we could alternatively flush here to get plant_obj an id if new
    if plant_obj.id:
        tag_objects = get_sql_session().query(Tag).filter(Tag.plant == plant_obj).all()
        for tag_object in tag_objects:
            if not [t for t in tags if t.get('id') == tag_object.id] and tag_object not in new_list:
                get_sql_session().delete(tag_object)

    return new_list

