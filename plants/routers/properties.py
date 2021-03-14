from fastapi import APIRouter, Depends
import logging
from pydantic.error_wrappers import ValidationError
from sqlalchemy.orm import Session
from starlette.requests import Request

from plants.util.ui_utils import get_message, make_list_items_json_serializable, throw_exception
from plants.validation.plant_validation import PPlantIdOptional
from plants.validation.property_validation import PResultsPropertiesForPlant, PPropertiesModifiedPlant, \
    PPropertiesModifiedTaxon
from plants.services.property_services import SaveProperties, LoadProperties, SavePropertiesTaxa
from plants.dependencies import get_db
from plants.validation.message_validation import PConfirmation
logger = logging.getLogger(__name__)


router = APIRouter(
        responses={404: {"description": "Not found"}},
        tags=['properties'],
        dependencies=[Depends(get_db)],
        )


@router.post("/taxon_properties/")
async def modify_taxon_properties(
        request: Request,
        data: PPropertiesModifiedTaxon,
        db: Session = Depends(get_db)):
    """taxon properties; note: there's no get method for taxon properties; they are read with the plant's
        properties
        save taxon properties"""

    SavePropertiesTaxa().save_properties(properties_modified=data.modifiedPropertiesTaxa, db=db)
    results = {'action':   'Update',
               'resource': 'PropertyTaxaResource',
               'message':  get_message(f'Updated properties for taxa in database.')
               }

    # evaluate output
    try:
        PConfirmation(**results)
    except ValidationError as err:
        throw_exception(str(err), request=request)

    return results  # required for closing busy dialog when saving


@router.post("/plant_properties/")
async def modify_plant_properties(
        request: Request,
        data: PPropertiesModifiedPlant,
        db: Session = Depends(get_db)):
    """save plant properties"""

    SaveProperties().save_properties(data.modifiedPropertiesPlants, db=db)
    results = {'action':   'Update',
               'resource': 'PropertyResource',
               'message':  get_message(f'Updated properties in database.')
               }

    # evaluate output
    try:
        PConfirmation(**results)
    except ValidationError as err:
        throw_exception(str(err), request=request)

    return results  # required for closing busy dialog when saving


@router.get("/plant_properties/{plant_id}")
def get_plant_properties(
        request: Request,
        plant_id: int,
        taxon_id: int = None,
        db: Session = Depends(get_db)):
    """reads a plant's property values from db; plus it's taxon's property values"""
    if not plant_id:
        throw_exception('Plant id required for Property GET requests', request=request)
    if plant_id == 'undefined':
        plant_id = None

    # evaluate arguments
    try:
        PPlantIdOptional.parse_obj(plant_id)
    except ValidationError as err:
        throw_exception(str(err), request=request)

    load_properties = LoadProperties()
    categories = load_properties.get_properties_for_plant(plant_id, db)

    # categories_taxon = load_properties.get_properties_for_taxon(int(request.args['taxon_id'])) if request.args.get(
    #         'taxon_id') else []
    categories_taxon = load_properties.get_properties_for_taxon(taxon_id, db) if taxon_id else []

    make_list_items_json_serializable(categories)
    make_list_items_json_serializable(categories_taxon)

    results = {
        'propertyCollections':      {"categories": categories},
        'plant_id':                 plant_id,
        'propertyCollectionsTaxon': {"categories": categories_taxon},
        'taxon_id':                 taxon_id,

        'action':                   'Get',
        'resource':                 'PropertyTaxaResource',
        'message':                  get_message(f"Receiving properties for {plant_id} from database.")
        }

    # evaluate output
    try:
        PResultsPropertiesForPlant(**results)
    except ValidationError as err:
        throw_exception(str(err), request=request)

    return results
