from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends

# if TYPE_CHECKING:
from plants.dependencies import get_image_dal, get_taxon_dal, valid_taxon
from plants.modules.biodiversity.taxonomy_name_formatter import (
    BotanicalNameInput,
    create_formatted_botanical_name,
)

# if TYPE_CHECKING:
from plants.modules.image.image_dal import ImageDAL
from plants.modules.taxon.models import Taxon
from plants.modules.taxon.schemas import (
    CreateBotanicalNameRequest,
    CreateBotanicalNameResponse,
    CreateTaxonResponse,
    GetTaxonResponse,
    TaxonCreate,
    UpdateTaxaRequest,
)
from plants.modules.taxon.services import modify_taxon, save_new_taxon
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.enums import MajorResource
from plants.shared.message_schemas import BackendSaveConfirmation
from plants.shared.message_services import get_message

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/taxa",
    tags=["taxa"],
    responses={404: {"description": "Not found"}},
)


@router.post("/botanical_name", response_model=CreateBotanicalNameResponse)
async def create_botanical_name(botanical_attributes: CreateBotanicalNameRequest) -> Any:
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


@router.get("/{taxon_id}", response_model=GetTaxonResponse)
async def get_taxon(taxon: Taxon = Depends(valid_taxon)) -> Any:
    """Returns taxon for requested taxon_id."""

    return {
        "action": "Get taxa",
        "message": get_message(f"Read taxon {taxon.id} from database."),
        "taxon": taxon,
    }


@router.post("/new", response_model=CreateTaxonResponse)
async def save_taxon(
    new_taxon_data: TaxonCreate,
    background_tasks: BackgroundTasks,
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
) -> Any:
    """Save a custom or non-custom taxon from search results list; if taxon already is in db, just
    return it."""
    logger.info(
        f"Received request to save taxon if not exists: ID={new_taxon_data.id}, LSID: "
        f"{new_taxon_data.lsid}"
    )
    if new_taxon_data.id:
        taxon: Taxon = await taxon_dal.by_id(new_taxon_data.id)
        msg = get_message(f"Loaded {taxon.name} from database.")
    else:
        taxon = await save_new_taxon(
            new_taxon_data, taxon_dal=taxon_dal, background_tasks=background_tasks
        )
        msg = get_message(f"Saved taxon {taxon.name} to database.")
        taxon = await taxon_dal.by_id(taxon.id)

    return {"action": "Save taxon", "message": msg, "new_taxon": taxon}


@router.put("/", response_model=BackendSaveConfirmation)
async def update_taxa(
    modified_taxa: UpdateTaxaRequest,
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
    image_dal: ImageDAL = Depends(get_image_dal),
) -> Any:
    """Update 1..n taxa in database."""
    for taxon_modified in modified_taxa.ModifiedTaxaCollection:
        await modify_taxon(taxon_modified=taxon_modified, taxon_dal=taxon_dal, image_dal=image_dal)

    results = {
        "resource": MajorResource.TAXON,
        "message": get_message(
            msg := f"Updated {len(modified_taxa.ModifiedTaxaCollection)} taxa in " f"database."
        ),
    }
    logger.info(msg)
    return results
