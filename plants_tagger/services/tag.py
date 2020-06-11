from datetime import datetime

from flask_2_ui5_py import throw_exception

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.plant_models import Tag, Plant


def tag_modified(tag_obj: Tag, tag_dict: dict):
    """returns true if dict values are different from orm object properties"""
    for key, value in tag_dict.items():
        if value != tag_obj.__dict__[key] and key != 'last_update':
            return True
    return False


def update_tag(tag_obj: Tag, tag_dict: dict):
    """updates the orm object from dict values"""
    tag_obj.text = tag_dict['text']
    tag_obj.icon = tag_dict['icon']
    tag_obj.state = tag_dict['state']
    tag_obj.last_update = datetime.now()

    # plant_id = get_sql_session().query(Plant.id).filter(Plant.plant_name == tag_dict['plant_name']).scalar()
    # if not plant_id:
    #     throw_exception(f"Can't find plant id for plant {tag_dict['plant_name']}")
    # # tag_obj.plant_name = tag_dict['plant_name']
    # tag_obj.plant_id = plant_id
    tag_obj.plant_id = tag_dict['plant_id']
