from collections import defaultdict

from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Soil, SoilComponent, SoilToComponentAssociation


def get_or_create_soil(soil_dict: dict, counts: defaultdict):
    """returns the soil described in dictionary; if not exists, generates it with components included"""
    # we don't rely on the id coming from the frontend (too much mess there), but use the soil_name
    soil_obj = get_sql_session().query(Soil).filter(Soil.soil_name == soil_dict['soil_name'].strip()).first()
    if soil_obj:
        return soil_obj

    # create soil in database
    soil_obj = Soil(soil_name=soil_dict.get('soil_name'))
    get_sql_session().add(soil_obj)
    get_sql_session().commit()
    counts['Added Soils'] += 1

    # get or create the soil components in database
    for component in soil_dict['components']:
        component_obj = get_sql_session().query(SoilComponent).filter(SoilComponent.component_name ==
                                                                      component.get('component_name').strip()).first()
        if not component_obj:
            component_obj = SoilComponent(component_name=component.get('component_name').strip())
            get_sql_session().add(component_obj)
            get_sql_session().commit()
            counts['Added Soil Components'] += 1

        # connect soil with the component
        # not very pythonic, but without committing, we need to populate the association table itself to
        # edit the portion in it
        association = SoilToComponentAssociation(soil=soil_obj,
                                                 soil_component=component_obj,
                                                 portion=component.get('portion'))
        get_sql_session().add(association)
        get_sql_session().commit()
        counts['Added Soil to Component Associations'] += 1

    return soil_obj


