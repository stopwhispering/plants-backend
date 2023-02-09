from fastapi import APIRouter, Depends
import logging
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.property.property_dal import PropertyDAL
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.api_utils import make_list_items_json_serializable
from plants.shared.message_services import get_message
from plants.modules.property.schemas import (BResultsPropertiesForPlant, FPropertiesModifiedPlant,
                                             FPropertiesModifiedTaxon, BResultsPropertyNames)
from plants.modules.property.services import SaveProperties, SavePropertiesTaxa, LoadProperties
from plants.dependencies import valid_plant, get_property_dal, get_taxon_dal, get_plant_dal
from plants.shared.message_schemas import BSaveConfirmation
from plants.shared.enums import FBMajorResource

logger = logging.getLogger(__name__)

router = APIRouter(
    responses={404: {"description": "Not found"}},
    tags=['properties'],
)


@router.post("/taxon_properties/", response_model=BSaveConfirmation)
async def create_or_update_taxon_properties(
        data: FPropertiesModifiedTaxon,
        property_dal: PropertyDAL = Depends(get_property_dal),
        taxon_dal: TaxonDAL = Depends(get_taxon_dal)):
    """note: there's no get method for taxon properties; they are read with the plant's
        properties; save new and modified taxon properties"""

    saver = SavePropertiesTaxa(property_dal=property_dal, taxon_dal=taxon_dal)
    await saver.save_properties(properties_modified=data.modifiedPropertiesTaxa)
    results = {'resource': FBMajorResource.TAXON_PROPERTIES,
               'message': get_message(f'Updated properties for taxa in database.')
               }

    return results


@router.post("/plant_properties/", response_model=BSaveConfirmation)
async def modify_plant_properties(
        data: FPropertiesModifiedPlant,
        property_dal: PropertyDAL = Depends(get_property_dal),
        plant_dal: PlantDAL = Depends(get_plant_dal)
):
    """save plant properties"""
    saver = SaveProperties(property_dal=property_dal, plant_dal=plant_dal)
    await saver.save_properties(data.modifiedPropertiesPlants)
    results = {'resource': FBMajorResource.PLANT_PROPERTIES,
               'message': get_message(f'Updated properties in database.')
               }

    return results


@router.get("/plant_properties/{plant_id}", response_model=BResultsPropertiesForPlant)
async def get_plant_properties(
        plant: Plant = Depends(valid_plant),
        taxon_id: int = None,  # todo works??
        property_dal: PropertyDAL = Depends(get_property_dal),
        taxon_dal: TaxonDAL = Depends(get_taxon_dal)):
    """reads a plant's property values from db; plus it's taxon's property values"""

    load_properties = LoadProperties(property_dal=property_dal, taxon_dal=taxon_dal)
    categories = await load_properties.get_properties_for_plant(plant)

    categories_taxon = await load_properties.get_properties_for_taxon(taxon_id) if taxon_id else []

    make_list_items_json_serializable(categories)
    make_list_items_json_serializable(categories_taxon)

    results = {
        'propertyCollections': {"categories": categories},
        'plant_id': plant.id,
        'propertyCollectionsTaxon': {"categories": categories_taxon},
        'taxon_id': taxon_id,
        'action': 'Get',
        'message': get_message(f"Receiving properties for plant {plant.id} from database.")
    }
    return results


@router.get("/property_names/", response_model=BResultsPropertyNames)
async def get_property_names(property_dal: PropertyDAL = Depends(get_property_dal)):
    category_obj = await property_dal.get_all_property_categories()
    categories = {}
    for cat in category_obj:
        # todo switch to orm mode
        categories[cat.category_name] = [{'property_name': p.property_name,
                                          'property_name_id': p.id,
                                          'countPlants': len(p.property_values)
                                          } for p in cat.property_names]

    results = {
        'action': 'Get',
        'propertiesAvailablePerCategory': categories,
        'message': get_message(f"Receiving Property Names from database.")
    }

    return results
