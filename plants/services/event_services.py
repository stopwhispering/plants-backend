from collections import defaultdict

from sqlalchemy.orm import Session

from plants.models.event_models import Soil, SoilComponent, SoilToComponentAssociation


def get_or_create_soil(soil_dict: dict, counts: defaultdict, db: Session):
    """returns the soil described in dictionary; if not exists, generates it"""
    # we don't rely on the id coming from the frontend (too much mess there), but use the soil_name
    soil_obj = db.query(Soil).filter(Soil.soil_name == soil_dict['soil_name'].strip()).first()
    if soil_obj:
        return soil_obj

    # create soil in database
    soil_obj = Soil(soil_name=soil_dict.get('soil_name'),
                    mix=soil_dict.get('mix'),
                    description=soil_dict.get('description'))
    db.add(soil_obj)
    db.commit()
    counts['Added Soils'] += 1

    # # get or create the soil components in database
    # for component in soil_dict['components']:
    #     component_obj = db.query(SoilComponent).filter(SoilComponent.component_name ==
    #                                                    component.get('component_name').strip()).first()
    #     if not component_obj:
    #         component_obj = SoilComponent(component_name=component.get('component_name').strip())
    #         db.add(component_obj)
    #         db.commit()
    #         counts['Added Soil Components'] += 1
    #
    #     # connect soil with the component
    #     # not very pythonic, but without committing, we need to populate the association table itself to
    #     # edit the portion in it
    #     association = SoilToComponentAssociation(soil=soil_obj,
    #                                              soil_component=component_obj,
    #                                              portion=component.get('portion'))
    #     db.add(association)
    #     db.commit()
    #     counts['Added Soil to Component Associations'] += 1

    return soil_obj
