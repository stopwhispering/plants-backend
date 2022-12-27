from threading import Thread
import logging
from sqlalchemy.orm import Session

from plants.services.taxonomy_lookup_details import TaxonomyLookupDetails
from plants.util.ui_utils import throw_exception
from plants.services.taxonomy_occurence_images import TaxonOccurencesLoader
from plants.validation.taxon_validation import (
    FAssignTaxonRequest, BSearchResultSource
)
from plants.services.taxonomy_lookup_gbif_id import GBIFIdentifierLookup
from plants.models.taxon_models import Taxon

logger = logging.getLogger(__name__)


def retrieve_taxon_details(retrieve_taxon_details_request: FAssignTaxonRequest, db: Session) -> Taxon:
    taxon = None

    # easy case: taxon is already in database and no custom taxon is to be created
    if (retrieve_taxon_details_request.source == BSearchResultSource.SOURCE_PLANTS_DB
            and not retrieve_taxon_details_request.hasCustomName):
        taxon = db.query(Taxon).filter(Taxon.id == retrieve_taxon_details_request.taxon_id).first()
        if not taxon:
            logger.error(f"Can't find {retrieve_taxon_details_request.taxon_id} / "
                         f"{retrieve_taxon_details_request.nameInclAddition} in database.")
            throw_exception(f"Can't find {retrieve_taxon_details_request.taxon_id} / "
                            f"{retrieve_taxon_details_request.nameInclAddition} in database.")

    # taxon is already in database, but the user entered a custom name
    # that custom name might already exist in database as well
    elif (retrieve_taxon_details_request.source == BSearchResultSource.SOURCE_PLANTS_DB
          and retrieve_taxon_details_request.hasCustomName):
        taxon = db.query(Taxon).filter(Taxon.name == retrieve_taxon_details_request.nameInclAddition,
                                       Taxon.is_custom).first()
        if taxon:
            logger.info(f'Found custom name in database: {retrieve_taxon_details_request.nameInclAddition}')

    # either taxon data was requested from kew databases or the local db does not contain the taxon
    # retrieve information from Kew databases POWO and IPNI and create new taxon db record
    if not taxon:
        taxonomy_lookup_details = TaxonomyLookupDetails(db=db)
        taxon = taxonomy_lookup_details.lookup(retrieve_taxon_details_request.lsid,
                                               retrieve_taxon_details_request.hasCustomName,
                                               retrieve_taxon_details_request.nameInclAddition)
        taxonomy_lookup_details.save_taxon(taxon)

    # The (meta-)database "Global Biodiversity Information Facility" (GBIF) has distribution information,
    # a well-documented API and contains entries from dozens of databases; get an ID for it and save it, too
    # todo: use that data... especially distribution information is far better than what is curr. used
    if not taxon.is_custom:
        gbif_identifier_lookup = GBIFIdentifierLookup()
        gbif_id = gbif_identifier_lookup.lookup(taxon_name=taxon.name, lsid=taxon.lsid)
        if gbif_id:
            taxon.gbif_id = gbif_id
            db.commit()

            # lookup ocurrences & image URLs at GBIF and generate thumbnails for found image URLs
            loader = TaxonOccurencesLoader(db=db)
            thread = Thread(target=loader.scrape_occurrences_for_taxon, args=[gbif_id])
            logger.info(f'Starting thread to load occurences for gbif_id {gbif_id}')
            thread.start()

    return taxon
