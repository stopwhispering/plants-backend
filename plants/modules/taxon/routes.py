import logging

from fastapi import APIRouter, Depends

from plants.modules.plant.image_dal import ImageDAL
from plants.modules.plant.taxon_dal import TaxonDAL
from plants.modules.taxon.services import modify_taxon, save_new_taxon
from plants.modules.biodiversity.taxonomy_name_formatter import create_formatted_botanical_name, BotanicalNameInput
from plants.shared.message_services import get_message
from plants.modules.taxon.models import Taxon
from plants.dependencies import valid_taxon, get_taxon_dal, get_image_dal
from plants.shared.message_schemas import BSaveConfirmation, FBMajorResource
from plants.modules.taxon.schemas import (
    FModifiedTaxa, BResultsGetTaxon, FBotanicalAttributes,
    BResultsGetBotanicalName, FNewTaxon, BCreatedTaxonResponse)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/taxa",
    tags=["taxa"],
    responses={404: {"description": "Not found"}},
)


@router.post("/botanical_name", response_model=BResultsGetBotanicalName)
async def create_botanical_name(botanical_attributes: FBotanicalAttributes):
    """
    create a botanical name incl. formatting (italics) for supplied taxon attributes
    """
    botanical_name_input = BotanicalNameInput(
        rank=botanical_attributes.rank,
        genus=botanical_attributes.genus,
        species=botanical_attributes.species,
        infraspecies=botanical_attributes.infraspecies,
        hybrid=botanical_attributes.hybrid,
        hybridgenus=botanical_attributes.hybridgenus,
        is_custom=botanical_attributes.is_custom,
        cultivar=botanical_attributes.cultivar,
        affinis=botanical_attributes.affinis,
        custom_rank=botanical_attributes.custom_rank,
        custom_infraspecies=botanical_attributes.custom_infraspecies,
        authors=botanical_attributes.authors,
        name_published_in_year=botanical_attributes.name_published_in_year,
        custom_suffix=botanical_attributes.custom_suffix,
    )
    name = create_formatted_botanical_name(botanical_attributes=botanical_name_input,
                                           include_publication=False,
                                           html=False)
    full_html_name = create_formatted_botanical_name(botanical_attributes=botanical_name_input,
                                                     include_publication=True,
                                                     html=True)
    return {
        'name': name,
        'full_html_name': full_html_name,
    }


@router.get("/{taxon_id}", response_model=BResultsGetTaxon)
async def get_taxon(taxon: Taxon = Depends(valid_taxon)):
    """
    returns taxon for requested taxon_id
    """
    return {'action': 'Get taxa',
            'message': get_message(f'Read taxon {taxon.id} from database.'),
            'taxon': taxon}


@router.post("/new", response_model=BCreatedTaxonResponse)
async def save_taxon(new_taxon_data: FNewTaxon, taxon_dal: TaxonDAL = Depends(get_taxon_dal)):
    """
    save a custom or non-custom taxon from search results list; if taxon already is in db, just return it
    """
    logger.info(f'Received request to save taxon if not exists: ID={new_taxon_data.id}, LSID: {new_taxon_data.lsid}')
    if new_taxon_data.id:
        taxon: Taxon = taxon_dal.by_id(new_taxon_data.id)
        msg = get_message(f'Loaded {taxon.name} from database.')
    else:
        taxon: Taxon = save_new_taxon(new_taxon_data, taxon_dal=taxon_dal)
        msg = get_message(f'Saved taxon {taxon.name} to database.')

    return {
        'action': 'Save taxon',
        'message': msg,
        'new_taxon': taxon
    }


@router.put("/", response_model=BSaveConfirmation)
async def update_taxa(modified_taxa: FModifiedTaxa,
                      taxon_dal: TaxonDAL = Depends(get_taxon_dal),
                      image_dal: ImageDAL = Depends(get_image_dal)):
    """
    update 1..n taxa in database
    """
    modified_taxa = modified_taxa.ModifiedTaxaCollection
    for taxon_modified in modified_taxa:
        modify_taxon(taxon_modified=taxon_modified, taxon_dal=taxon_dal, image_dal=image_dal)

    results = {'resource': FBMajorResource.TAXON,
               'message': get_message(msg := f'Updated {len(modified_taxa)} taxa in database.')
               }
    logger.info(msg)
    return results
