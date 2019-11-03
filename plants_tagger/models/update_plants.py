import datetime
import logging

from plants_tagger.models.os_paths import SUBDIRECTORY_PHOTOS_SEARCH
from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Plant, Taxon, Tag
from plants_tagger.util.exif_helper import decode_record_date_time
from plants_tagger.util.tag_util import tag_modified, update_tag

logger = logging.getLogger(__name__)


def update_plants_from_list_of_dicts(plants: [dict]):

    new_list = []
    logger.info(f"Updating/Creating {len(plants)} plants")
    for plant in plants:
        record_update = get_sql_session().query(Plant).filter_by(plant_name=plant['plant_name']).first()
        boo_new = False if record_update else True

        if boo_new:
            if [r for r in new_list if r.plant_name == plant['plant_name']]:
                continue  # same plant in multiple new records
            # create new record (as object) & add to list later)
            record_update = Plant(plant_name=plant['plant_name'])
            logger.info(f'Saving new plant {plant["plant_name"]}')

        # catch key errors (new entries don't have all keys in the dict)
        record_update.plant_name = plant['plant_name']   # key is always supplied
        record_update.species = plant['species'] if 'species' in plant else None
        record_update.count = plant['count'] if 'count' in plant else None
        record_update.active = plant['active'] if 'active' in plant else None
        # record_update.dead = plant['dead'] if 'dead' in plant else None
        if 'generation_date' not in plant or not plant['generation_date']:
            record_update.generation_date = None
        else:
            record_update.generation_date = decode_record_date_time(plant['generation_date'])
        record_update.generation_type = plant['generation_type'] if 'generation_type' in plant else None
        record_update.generation_notes = plant['generation_notes'] if 'generation_notes' in plant else None
        record_update.mother_plant = plant['mother_plant'] if 'mother_plant' in plant else None
        record_update.generation_origin = plant['generation_origin'] if 'generation_origin' in plant else None
        record_update.plant_notes = plant['plant_notes'] if 'plant_notes' in plant else None

        if 'filename_previewimage' in plant and plant['filename_previewimage']:
            # we need to remove the localService prefix
            filename_previewimage = plant['filename_previewimage'].replace('\\\\', '\\')
            logger.debug(f"Saving {plant['plant_name']}, setting preview image as {filename_previewimage}")
            if filename_previewimage.startswith(SUBDIRECTORY_PHOTOS_SEARCH):
                filename_previewimage_modified = filename_previewimage[len(SUBDIRECTORY_PHOTOS_SEARCH):]
                logger.debug(f"Changing to {filename_previewimage_modified}")
                record_update.filename_previewimage = filename_previewimage_modified
            else:
                record_update.filename_previewimage = filename_previewimage
        else:
            record_update.filename_previewimage = None

        # save taxon
        if 'taxon_id' in plant:  # empty for newly created plants
            taxon = get_sql_session().query(Taxon).filter(Taxon.id == plant['taxon_id']).first()
            if taxon:
                record_update.taxon = taxon
            else:
                logger.error(f"Taxon with id {plant['taxon_id']} not found. Skipped taxon assignment.")

        record_update.last_update = datetime.datetime.now()

        # save tags
        if 'tags' in plant:
            for tag in plant['tags']:
                # new tag
                if 'id' not in tag:
                    tag_object: Tag = Tag(text=tag['text'],
                                          icon=tag['icon'],
                                          state=tag['state'],
                                          plant=record_update,
                                          last_update=datetime.datetime.now())
                    new_list.append(tag_object)
                else:
                    # update if modified (not implemented in frontend)
                    tag_object = get_sql_session().query(Tag).filter(Tag.id == tag['id']).first()
                    if tag_modified(tag_object, tag):
                        update_tag(tag_object, tag)

        # delete deleted tags from db
        tag_objects = get_sql_session().query(Tag).filter(Tag.plant == record_update).all()
        for tag_object in tag_objects:
            if not [t for t in plant['tags'] if t.get('id') == tag_object.id] and tag_object not in new_list:
                get_sql_session().delete(tag_object)

        if boo_new:
            new_list.append(record_update)

    if new_list:
        get_sql_session().add_all(new_list)

    get_sql_session().commit()  # saves changes in existing records, too
