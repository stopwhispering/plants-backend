# import logging
#
# from pykew import ipni as ipni, powo as powo
# from sqlalchemy.orm import Session
#
# from plants.models.taxon_models import Taxon, Distribution
# from plants.services.taxonomy_shared_functions import (
#     create_synonym_label_if_only_a_synonym, create_distribution_concat, create_synonyms_concat)
# from plants.validation.taxon_validation import FBRank
#
# logger = logging.getLogger(__name__)
#
#
# class TaxonomyLookupDetails:
#     def __init__(self, db: Session):
#         self.db = db
#
#     def lookup(self,
#                lsid: str,
#                has_custom_name: bool,
#                name_incl_addition: str) -> Taxon:
#         """try to find lsid in taxon table and return if existing;
#         otherwise retrieve information from kew databases "powo" and "ipni" and create new taxon db record"""
#         # make sure the entry really does not exist, yet
#         if taxon := self._get_taxon_from_db(lsid, has_custom_name, name_incl_addition):
#             logger.warning('Taxon unexpectedly found in database.')
#             return taxon
#
#         logger.info(f'Copying taxon {lsid} from kew databases powo and ipni.')
#         # get taxon information from kpew databases "IPNI" and "POWO"
#         # IPNI always returns a result (otherwise we wouldn't come here), POWO has slightly less plants in the db
#         ipni_lookup = ipni.lookup_name(lsid)
#         powo_lookup = powo.lookup(lsid, include=['distribution']) if ipni_lookup.get('inPowo') else None
#         if 'error' in powo_lookup:
#             powo_lookup = {}
#
#         # treat infraspecific taxa
#         # a taxon may have 0 or 1 infra-specific name, never multiple
#         if (rank := ipni_lookup.get('rank')) == FBRank.GENUS.value:
#             species = None
#             infraspecies = None
#         elif rank == FBRank.SPECIES.value:
#             species = ipni_lookup.get('species')
#             infraspecies = None
#         elif rank in (FBRank.SUBSPECIES.value, FBRank.VARIETY.value, FBRank.FORMA.value):
#             species = ipni_lookup.get('species')
#             infraspecies = ipni_lookup.get('infraspecies')
#         else:
#             raise ValueError(f'Unexpected rank {rank} for {lsid}.')
#
#         taxon = Taxon(
#             name=name_incl_addition if has_custom_name else ipni_lookup.get('name'),
#             is_custom=True if has_custom_name else False,
#             lsid=lsid,
#             # phylum=powo_lookup.get('phylum'),
#             family=ipni_lookup.get('family'),
#             genus=ipni_lookup.get('genus'),
#             species=species,
#             infraspecies=infraspecies,
#             # cultivar=  # always custom
#             # affinis=  # always custom
#             rank=rank,
#             taxonomic_status=powo_lookup.get('taxonomicStatus'),
#             name_published_in_year=powo_lookup.get('namePublishedInYear', ipni_lookup.get('publicationYear')),
#             synonym=powo_lookup.get('synonym'),
#             authors=powo_lookup.get('authors', ipni_lookup.get('authors')),
#             hybrid=ipni_lookup.get('hybrid'),
#             hybridgenus=ipni_lookup.get('hybridGenus'),
#             basionym=powo_lookup['basionym'].get('name') if powo_lookup.get('basionym') else None,
#             distribution_concat=create_distribution_concat(powo_lookup) if powo_lookup else None
#         )
#         if powo_lookup and not powo_lookup.get('synonym'):
#             taxon.synonyms_concat = create_synonyms_concat(powo_lookup)
#         elif powo_lookup and powo_lookup.get('synonym'):
#             taxon.synonyms_concat = create_synonym_label_if_only_a_synonym(powo_lookup['accepted']['name'])
#         else:
#             taxon.synonyms_concat = None
#
#         # todo implement generic solution
#         max_length = Taxon.synonyms_concat.expression.type.length
#         if len(taxon.synonyms_concat) > max_length:
#             taxon.synonyms_concat = taxon.synonyms_concat[:max_length-3] + '...'
#
#         # distribution
#         dist = []
#         if distribution := powo_lookup.get('distribution'):
#             distribution: dict
#             # collect native and introduced distribution into one list
#             if natives := distribution.get('natives'):
#                 dist.extend(natives)
#             if introduced := distribution.get('introduced'):
#                 dist.extend(introduced)
#
#         if not dist:
#             logger.info(f'No distribution info found for {taxon.name}.')
#         else:
#             for area in dist:
#                 record = Distribution(name=area.get('name'),
#                                       establishment=area.get('establishment'),
#                                       feature_id=area.get('featureId'),
#                                       tdwg_code=area.get('tdwgCode'),
#                                       tdwg_level=area.get('tdwgLevel')
#                                       )
#                 taxon.distribution.append(record)
#             logger.info(f'Found {len(dist)} areas for {taxon.name}.')
#
#         return taxon
#
#     def save_taxon(self, taxon: Taxon) -> None:
#         self.db.add(taxon)
#         self.db.commit()  # upon commit (flush), the ids are determined
#         logger.info(f'Retrieved data from kew databases and created taxon {taxon.name} in database.')
#
#     def _get_taxon_from_db(self, lsid: str, has_custom_name: bool, name_incl_addition: str) -> Taxon | None:
#         if has_custom_name:
#             # in case of custom name, the (conceptual) key consists of name + is_custom==True
#             taxon = self.db.query(Taxon).filter(Taxon.name == name_incl_addition,
#                                                 Taxon.is_custom is True).first()
#         # otherwise, the (conceptual) key consists of the lsid + is_custom==False
#         else:
#             taxon = self.db.query(Taxon).filter(Taxon.lsid == lsid,
#                                                 Taxon.is_custom is False).first()
#         if taxon:
#             return taxon
