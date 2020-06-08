import logging
from typing import Iterable

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.services.TaxonCompileModel import TaxonCompileModel
from plants_tagger.services.TaxonLookup import TaxonLookup

logger = logging.getLogger(__name__)


def copy_taxon_from_kew2(lsid: str,
                         has_custom_name: bool = False,
                         name_incl_addition: str = None,
                         databases: Iterable[str] = ('ipni', 'powo', 'gbif'),
                         overwrite: bool = False):
    """try to find fqId in taxon table and return if existing;
    otherwise retrieve information from kew databases and create new extensions entry"""
    custom_name_full = name_incl_addition if has_custom_name else None
    logger.info(f'Copying taxon {lsid} from plants databases: {databases}')
    # get taxon information from pew databases ipni and powo
    # ipni always returns a result (otherwise we wouldn't come here), powo is optional
    taxon_lookup = TaxonLookup(lsid=lsid, databases=databases, databases_parent=('gbif', 'ipni',))
    lookup_taxon = taxon_lookup.lookup_taxon()
    lookups_parents = taxon_lookup.lookup_parents()

    # get new orm objects for taxon and then for parent taxa
    # new list might include area/distribution orm objects as well
    add_list = []
    taxon, add_list_tmp = TaxonCompileModel().get_model(lookups=lookup_taxon,
                                                        overwrite=overwrite,
                                                        custom_name_full=custom_name_full)
    add_list.extend(add_list_tmp)
    for lookup in lookups_parents:
        taxon_parent, add_list_tmp = TaxonCompileModel().get_model(lookups=lookup,
                                                                   overwrite=overwrite)
        add_list.extend(add_list_tmp)
        # set parent-child relationship
        taxon.parent = taxon_parent
        taxon = taxon_parent

    if add_list:
        get_sql_session().add_all(add_list)
    get_sql_session().commit()  # upon commit (flush), the ids are determined
    logger.info(f'Retrieved data from kew databases and created taxon {taxon.name} in database.')

    return taxon


# def taxon_exists2(lsid: str,
#                   has_custom_name: bool = False,
#                   name_incl_addition: str = None,):
