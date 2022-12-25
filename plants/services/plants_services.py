import datetime
import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from datetime import datetime
from datetime import date

from plants.models.image_models import ImageKeyword
from plants.models.plant_models import Plant
from plants.models.tag_models import Tag
from plants.services.tag_services import tag_modified, update_tag
from plants.util.ui_utils import throw_exception
from plants.validation.plant_validation import FBPlantTag, FBPlant

logger = logging.getLogger(__name__)


def update_plants_from_list_of_dicts(plants: List[FBPlant], db: Session) -> List[Plant]:
    new_list = []
    plants_saved = []
    logger.info(f"Updating/Creating {len(plants)} plants")
    for plant in plants:
        if plant.id is None:
            record_update = Plant(plant_name=plant.plant_name)
            if [r for r in new_list if isinstance(r, Plant) and r.plant_name == plant.plant_name]:
                # continue  # same plant in multiple new records
                throw_exception('Plant Name supplied multiple times.')
            if Plant.get_plant_by_plant_name(plant.plant_name, db):
                throw_exception('Plant Name already exists.')
                record_update = Plant(plant_name=plant.plant_name)
                logger.info(f'Creating new plant {plant.plant_name}')

            record_update.deleted = False
            new_list.append(record_update)
        else:
            record_update = Plant.get_plant_by_plant_id(plant.id, db)

        record_update.plant_name = plant.plant_name   # pseudo-key, is always supplied
        record_update.active = plant.active
        record_update.cancellation_reason = plant.cancellation_reason
        record_update.cancellation_date = plant.cancellation_date

        record_update.field_number = plant.field_number
        record_update.geographic_origin = plant.geographic_origin
        record_update.nursery_source = plant.nursery_source
        record_update.propagation_type = plant.propagation_type
        record_update.generation_notes = plant.generation_notes
        record_update.plant_notes = plant.plant_notes

        record_update.parent_plant_id = plant.parent_plant.id if plant.parent_plant else None
        record_update.parent_plant_pollen_id = plant.parent_plant_pollen.id if plant.parent_plant_pollen else None
        record_update.set_filename_previewimage(plant=plant)
        record_update.set_taxon(db=db, taxon_id=plant.taxon_id)
        record_update.set_last_update()

        # create new, update existing and remove deleted tags
        new_tags = _update_tags(record_update, plant.tags, db)
        new_list.extend(new_tags)

        plants_saved.append(record_update)

    if new_list:
        db.add_all(new_list)

    db.commit()  # saves changes in existing records, too
    return plants_saved


def _clone_instance(model_instance, clone_attrs: Optional[dict] = None):
    """
    generate a transient clone of sqlalchemy instance; supply primary key
    as dict
    """
    # get data of non-primary-key columns; exclude relationships
    table = model_instance.__table__
    non_pk_columns = [k for k in table.columns.keys() if k not in table.primary_key]
    data = {c: getattr(model_instance, c) for c in non_pk_columns}
    if clone_attrs:
        data.update(clone_attrs)
    return model_instance.__class__(**data)


def deep_clone_plant(plant_original: Plant, plant_name_clone: str, db: Session):
    """
    clone supplied plant
    includes duplication of events, photo_file-to-event assignments, properties, tags
    excludes descendant plants
    assignments to same instances of parent plants, parent plants pollen (nothing to do here)
    """
    cloned = []

    plant_clone: Plant = _clone_instance(plant_original, {'plant_name': plant_name_clone,  # noqa
                                                         'last_update': datetime.now()})
    plant_clone.set_last_update()
    cloned.append(plant_clone)

    for tag in plant_original.tags:
        tag_clone = _clone_instance(tag, {'last_update': datetime.now()})  # noqa
        tag_clone.plant = plant_clone
        cloned.append(tag_clone)

    for event in plant_original.events:
        event_clone = _clone_instance(event)  # noqa
        event_clone.plant = plant_clone
        cloned.append(event_clone)

        # photo_file-to-event associations via photo_file instances (no need to update these explicitly)
        for image in event.images:
            image.events.append(event_clone)

    for property_value in plant_original.property_values_plant:
        property_value_clone = _clone_instance(property_value)  # noqa
        property_value_clone.plant = plant_clone
        cloned.append(property_value_clone)

    db.add_all(cloned)
    db.commit()  # saves changes in existing records, too


def _update_tags(plant_obj: Plant, tags: List[FBPlantTag], db: Session):
    """update modified tags; returns list of new tags (not yet added or committed); removes deleted tags"""
    new_list = []
    if tags:
        for tag in tags:
            if not tag.id:
                # new tag
                tag_object: Tag = Tag(text=tag.text,
                                      # icon=tag.icon,
                                      state=tag.state,  # noqa  use_enum_values option used
                                      plant=plant_obj,
                                      # last_update=datetime.datetime.now()
                                      last_update=datetime.now()
                                      )
                new_list.append(tag_object)
            else:
                # update if modified (not implemented in frontend)
                tag_object = Tag.get_tag_by_tag_id(tag.id, db, raise_exception=True)
                if tag_modified(tag_object, tag):
                    update_tag(tag_object, tag)

    # query raises exception for new plant objects that have no id, yet
    # we could alternatively flush here to get plant_obj an id if new
    if plant_obj.id:
        tag_objects = db.query(Tag).filter(Tag.plant == plant_obj).all()
        for tag_object in tag_objects:
            if not [t for t in tags if t.id == tag_object.id] and tag_object not in new_list:
                db.delete(tag_object)

    return new_list


def get_distinct_image_keywords(db: Session) -> set[str]:
    """
    get set of all image keywords
    """
    keyword_tuples = db.query(ImageKeyword.keyword).distinct().all()
    return {k[0] for k in keyword_tuples}


NULL_DATE = date(1900, 1, 1)
