from plants.modules.plant.models import Tag
from plants.modules.plant.schemas import FBPlantTag


def tag_modified(tag_current: Tag, tag_updated: FBPlantTag):
    """returns true if dict values are different from orm object properties"""
    return (  # tag_current.icon != tag_updated.icon or
            tag_current.text != tag_updated.text
            or tag_current.state != tag_updated.state
            or tag_current.plant_id != tag_updated.plant_id)


def update_tag(tag_obj: Tag, tag_dict: FBPlantTag):
    """updates the orm object from dict values"""
    tag_obj.text = tag_dict.text
    # tag_obj.icon = tag_dict.icon
    tag_obj.state = tag_dict.state
    # tag_obj.last_update = datetime.now()
    tag_obj.plant_id = tag_dict.plant_id