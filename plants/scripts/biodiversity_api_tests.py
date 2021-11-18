import logging

from plants.services.query_taxa import get_taxa_from_kew_databases

# get_taxa_from_kew_databases('Haworthia glauca*', [], False)
from plants.services.taxon_occurence_image_services import TaxonOccurencesLoader

logging.basicConfig(level=logging.DEBUG)


TaxonOccurencesLoader().scrape_occurrences_for_taxon(gbif_id='9620716', db=None)

a =1