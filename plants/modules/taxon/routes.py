import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from starlette.background import BackgroundTasks

from plants.dependencies import get_image_dal, get_taxon_dal, valid_taxon
from plants.modules.biodiversity.taxonomy_name_formatter import (
    BotanicalNameInput,
    create_formatted_botanical_name,
)
from plants.modules.taxon.schemas import (
    BCreatedTaxonResponse,
    BResultsGetBotanicalName,
    BResultsGetTaxon,
    FBotanicalAttributes,
    FModifiedTaxa,
    TaxonCreate,
)
from plants.modules.taxon.services import modify_taxon, save_new_taxon
from plants.shared.enums import MajorResource
from plants.shared.message_schemas import BSaveConfirmation
from plants.shared.message_services import get_message

if TYPE_CHECKING:
    from plants.modules.image.image_dal import ImageDAL
    from plants.modules.taxon.models import Taxon
    from plants.modules.taxon.taxon_dal import TaxonDAL

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/taxa",
    tags=["taxa"],
    responses={404: {"description": "Not found"}},
)


@router.post("/botanical_name", response_model=BResultsGetBotanicalName)
async def create_botanical_name(botanical_attributes: FBotanicalAttributes):
    """create a botanical name incl.

    formatting (italics) for supplied taxon attributes
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
    name = create_formatted_botanical_name(
        botanical_attributes=botanical_name_input, include_publication=False, html=False
    )
    full_html_name = create_formatted_botanical_name(
        botanical_attributes=botanical_name_input, include_publication=True, html=True
    )
    return {
        "name": name,
        "full_html_name": full_html_name,
    }


@router.get("/{taxon_id}", response_model=BResultsGetTaxon)
async def get_taxon(taxon: Taxon = Depends(valid_taxon)):
    """Returns taxon for requested taxon_id."""
    return {
        "action": "Get taxa",
        "message": get_message(f"Read taxon {taxon.id} from database."),
        "taxon": taxon,
    }


@router.post("/new", response_model=BCreatedTaxonResponse)
async def save_taxon(
    new_taxon_data: TaxonCreate,
    background_tasks: BackgroundTasks,
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
):
    """Save a custom or non-custom taxon from search results list; if taxon already is
    in db, just return it."""
    logger.info(
        f"Received request to save taxon if not exists: ID={new_taxon_data.id}, LSID: "
        f"{new_taxon_data.lsid}"
    )
    if new_taxon_data.id:
        taxon: Taxon = await taxon_dal.by_id(new_taxon_data.id)
        msg = get_message(f"Loaded {taxon.name} from database.")
    else:
        taxon: Taxon = await save_new_taxon(
            new_taxon_data, taxon_dal=taxon_dal, background_tasks=background_tasks
        )
        msg = get_message(f"Saved taxon {taxon.name} to database.")
        taxon: Taxon = await taxon_dal.by_id(taxon.id)

    return {"action": "Save taxon", "message": msg, "new_taxon": taxon}


@router.put("/", response_model=BSaveConfirmation)
async def update_taxa(
    modified_taxa: FModifiedTaxa,
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
    image_dal: ImageDAL = Depends(get_image_dal),
):
    """Update 1..n taxa in database."""
    modified_taxa = modified_taxa.ModifiedTaxaCollection
    for taxon_modified in modified_taxa:
        await modify_taxon(
            taxon_modified=taxon_modified, taxon_dal=taxon_dal, image_dal=image_dal
        )

    results = {
        "resource": MajorResource.TAXON,
        "message": get_message(
            msg := f"Updated {len(modified_taxa)} taxa in database."
        ),
    }
    logger.info(msg)
    return results
