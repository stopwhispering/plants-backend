from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi.concurrency import run_in_threadpool
from pykew import powo

if TYPE_CHECKING:
    from fastapi import BackgroundTasks

from plants.exceptions import TaxonAlreadyExistsError
from plants.modules.biodiversity.lookup_gbif_id import lookup_gbif_id
from plants.modules.biodiversity.taxonomy_name_formatter import (
    BotanicalNameInput,
    create_formatted_botanical_name,
)
from plants.modules.biodiversity.taxonomy_occurence_images import TaxonOccurencesLoader
from plants.modules.image.models import Image, ImageToTaxonAssociation
from plants.modules.taxon.models import Distribution, Taxon

if TYPE_CHECKING:
    from plants.modules.image.image_dal import ImageDAL
    from plants.modules.taxon.schemas import TaxonCreate, TaxonUpdate
    from plants.modules.taxon.taxon_dal import TaxonDAL

logger = logging.getLogger(__name__)


def _create_names(new_taxon: TaxonCreate) -> tuple[str, str]:
    """Create a simple and a html-formatted botanical name."""
    botanical_name_input = BotanicalNameInput(
        rank=new_taxon.rank,
        genus=new_taxon.genus,
        species=new_taxon.species,
        infraspecies=new_taxon.infraspecies,
        hybrid=new_taxon.hybrid,
        hybridgenus=new_taxon.hybridgenus,
        is_custom=new_taxon.is_custom,
        cultivar=new_taxon.cultivar,
        affinis=new_taxon.affinis,
        custom_rank=new_taxon.custom_rank,
        custom_infraspecies=new_taxon.custom_infraspecies,
        authors=new_taxon.authors,
        name_published_in_year=new_taxon.name_published_in_year,
        custom_suffix=new_taxon.custom_suffix,
    )
    full_html_name = create_formatted_botanical_name(
        botanical_attributes=botanical_name_input, include_publication=True, html=True
    )
    name = create_formatted_botanical_name(
        botanical_attributes=botanical_name_input, include_publication=False, html=False
    )
    return name, full_html_name


async def _retrieve_locations(lsid: str) -> list[Distribution]:
    powo_lookup = await run_in_threadpool(powo.lookup, lsid, include=["distribution"])
    locations: list[Distribution] = []

    # collect native and introduced distribution into one list
    dist = []
    if distribution := powo_lookup.get("distribution"):
        if natives := distribution.get("natives"):
            dist.extend(natives)
        if introduced := distribution.get("introduced"):
            dist.extend(introduced)

    if not dist:
        logger.info(f"No locations found for {lsid}.")
    else:
        for area in dist:
            record = Distribution(
                name=area.get("name"),
                establishment=area.get("establishment"),
                feature_id=area.get("featureId"),
                tdwg_code=area.get("tdwgCode"),
                tdwg_level=area.get("tdwgLevel"),
            )
            locations.append(record)
    return locations


async def save_new_taxon(
    new_taxon: TaxonCreate, taxon_dal: TaxonDAL, background_tasks: BackgroundTasks
) -> Taxon:
    """Save supplied taxon from frontend in the database."""
    name, full_html_name = _create_names(new_taxon)

    if new_taxon.is_custom:
        if not (
            (new_taxon.custom_rank and new_taxon.custom_infraspecies)
            or new_taxon.custom_suffix
            or new_taxon.cultivar
            or new_taxon.affinis
        ):
            raise ValueError("Custom fields not set for custom taxon.")
        locations = []
        gbif_id = None
    else:
        if any(
            [
                new_taxon.custom_rank,
                new_taxon.custom_infraspecies,
                new_taxon.custom_suffix,
                new_taxon.cultivar,
                new_taxon.affinis,
            ]
        ):
            raise ValueError("Custom fields unexpectedly set for non-custom taxon.")
        locations = await _retrieve_locations(new_taxon.lsid)

        # gbif_id = await run_in_threadpool(
        #     lookup_gbif_id, taxon_name=name, lsid=new_taxon.lsid
        # )

        gbif_id = await lookup_gbif_id(taxon_name=name, lsid=new_taxon.lsid)

    if await taxon_dal.exists(taxon_name=name):
        raise TaxonAlreadyExistsError(name)

    taxon = Taxon(
        name=name,
        full_html_name=full_html_name,
        gbif_id=gbif_id,
        distribution=locations,
        # attributes from ipni/powo
        rank=new_taxon.rank,
        # phylum=new_taxon.phylum,
        family=new_taxon.family,
        genus=new_taxon.genus,
        species=new_taxon.species,
        infraspecies=new_taxon.infraspecies,
        lsid=new_taxon.lsid,
        taxonomic_status=new_taxon.taxonomic_status,
        synonym=new_taxon.synonym,
        authors=new_taxon.authors,
        name_published_in_year=new_taxon.name_published_in_year,
        basionym=new_taxon.basionym,
        hybrid=new_taxon.hybrid,
        hybridgenus=new_taxon.hybridgenus,
        synonyms_concat=new_taxon.synonyms_concat,
        distribution_concat=new_taxon.distribution_concat,
        # custom attributes
        is_custom=new_taxon.is_custom,
        custom_rank=new_taxon.custom_rank,
        custom_infraspecies=new_taxon.custom_infraspecies,
        cultivar=new_taxon.cultivar,
        affinis=new_taxon.affinis,
        custom_suffix=new_taxon.custom_suffix,
        custom_notes="",
    )

    await taxon_dal.create(taxon)

    if gbif_id is not None:
        # lookup ocurrences & image URLs at GBIF and generate thumbnails for found image
        # URLs
        loader = TaxonOccurencesLoader(taxon_dal=taxon_dal)

        logger.info(f"Starting background task to load occurences for gbif_id " f"{str(gbif_id)}")
        background_tasks.add_task(loader.scrape_occurrences_for_taxon, gbif_id)

    return taxon


async def modify_taxon(
    taxon_modified: TaxonUpdate, taxon_dal: TaxonDAL, image_dal: ImageDAL
) -> None:
    taxon: Taxon = await taxon_dal.by_id(taxon_modified.id)

    if taxon.custom_notes != taxon_modified.custom_notes:
        await taxon_dal.update(taxon, {"custom_notes": taxon_modified.custom_notes})

    # changes to images attached to the taxon
    new_image_ids = {image.id for image in taxon_modified.images} if taxon_modified.images else {}
    new_images = {await image_dal.by_id(image_id) for image_id in new_image_ids}

    # remove images that are no longer assigned to the taxon
    image_obj: Image
    for image_obj in taxon.images[:]:
        if image_obj.id not in new_image_ids:
            taxon.images.remove(image_obj)
    # newly assigned images
    # if taxon_modified.images:
    for image_obj in new_images:
        image_description = (
            next(image.description for image in taxon_modified.images if image.id == image_obj.id)
            if taxon_modified.images
            else None
        )

        current_taxon_to_image_link = await taxon_dal.fetch_image_to_taxon_association(
            image_id=image_obj.id, taxon_id=taxon.id
        )

        # insert link
        if not current_taxon_to_image_link:
            link = ImageToTaxonAssociation(
                image_id=image_obj.id,
                taxon_id=taxon.id,
                description=image_description,
            )
            await taxon_dal.create_image_to_taxon_association(link)
            logger.info(f"Image {image_obj.id} assigned to taxon {taxon.name}")

        # update description
        elif current_taxon_to_image_link.description != image_description:
            current_taxon_to_image_link.description = image_description
            logger.info(
                f"Update description of link between image "
                f"{image_obj.id} and taxon {taxon.name}"
            )
