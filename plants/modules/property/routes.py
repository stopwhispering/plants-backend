from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session, subqueryload

from plants.util.ui_utils import get_message, make_list_items_json_serializable
from plants.modules.property.schemas import (BResultsPropertiesForPlant, FPropertiesModifiedPlant,
                                             FPropertiesModifiedTaxon, BResultsPropertyNames)
from plants.modules.property.services import SaveProperties, SavePropertiesTaxa, LoadProperties
from plants.dependencies import get_db
from plants.shared.message_schemas import BSaveConfirmation, FBMajorResource
from plants.modules.property.models import PropertyCategory


logger = logging.getLogger(__name__)

router = APIRouter(
        responses={404: {"description": "Not found"}},
        tags=['properties'],
        dependencies=[Depends(get_db)],
        )


@router.post("/taxon_properties/", response_model=BSaveConfirmation)
async def create_or_update_taxon_properties(
        data: FPropertiesModifiedTaxon,
        db: Session = Depends(get_db)):
    """note: there's no get method for taxon properties; they are read with the plant's
        properties; save new and modified taxon properties"""

    SavePropertiesTaxa().save_properties(properties_modified=data.modifiedPropertiesTaxa, db=db)
    results = {'resource': FBMajorResource.TAXON_PROPERTIES,
               'message':  get_message(f'Updated properties for taxa in database.')
               }

    return results


@router.post("/plant_properties/", response_model=BSaveConfirmation)
async def modify_plant_properties(
        data: FPropertiesModifiedPlant,
        db: Session = Depends(get_db)):
    """save plant properties"""

    SaveProperties().save_properties(data.modifiedPropertiesPlants, db=db)
    results = {'resource': FBMajorResource.PLANT_PROPERTIES,
               'message':  get_message(f'Updated properties in database.')
               }

    return results


@router.get("/plant_properties/{plant_id}", response_model=BResultsPropertiesForPlant)
def get_plant_properties(
        plant_id: int,
        taxon_id: int = None,
        db: Session = Depends(get_db)):
    """reads a plant's property values from db; plus it's taxon's property values"""

    load_properties = LoadProperties()
    categories = load_properties.get_properties_for_plant(plant_id, db)

    categories_taxon = load_properties.get_properties_for_taxon(taxon_id, db) if taxon_id else []

    make_list_items_json_serializable(categories)
    make_list_items_json_serializable(categories_taxon)

    results = {
        'propertyCollections':      {"categories": categories},
        'plant_id':                 plant_id,
        'propertyCollectionsTaxon': {"categories": categories_taxon},
        'taxon_id':                 taxon_id,
        'action':                   'Get',
        'message':                  get_message(f"Receiving properties for plant {plant_id} from database.")
        }
    return results


@router.get("/property_names/", response_model=BResultsPropertyNames)
async def get_property_names(db: Session = Depends(get_db)):
    query = db.query(PropertyCategory).options(subqueryload(PropertyCategory.property_names))
    category_obj = query.all()
    categories = {}
    for cat in category_obj:
        categories[cat.category_name] = [{'property_name':    p.property_name,
                                          'property_name_id': p.id,
                                          'countPlants':      len(p.property_values)
                                          } for p in cat.property_names]

    results = {
        'action':                         'Get',
        'propertiesAvailablePerCategory': categories,
        'message':                        get_message(f"Receiving Property Names from database.")
        }

    return results

