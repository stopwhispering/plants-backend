from datetime import datetime

from plants_tagger.models.tag_models import Tag


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
    tag_obj.plant_id = tag_dict['plant_id']
