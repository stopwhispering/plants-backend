import logging
from typing import List
from flask_2_ui5_py import throw_exception

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.taxon_models import Taxon
from plants_tagger.models.trait_models import TaxonToTraitAssociation, Trait, TraitCategory

logger = logging.getLogger(__name__)


def update_traits(taxon: Taxon, trait_categories: List[dict]):
    # update a taxon's traits (includes deleting and creating traits)

    # loop at new traits to update attributes and create new ones
    link: TaxonToTraitAssociation
    new_trait_obj_list = []
    for category_new in trait_categories or []:  # might be None
        # get category object
        category_obj = get_sql_session().query(TraitCategory).filter(TraitCategory.id == category_new.get('id')).first()
        if not category_obj:
            throw_exception(f'Trait Category {category_new.get("id")} not found.')

        # loop at category's traits
        for trait_new in category_new['traits']:

            # check if we have no trait id but a same-named trait
            if not trait_new.get('id'):
                trait_obj: Trait = get_sql_session().query(Trait).filter(
                        Trait.trait == trait_new.get('trait'),
                        Trait.trait_category == category_obj).first()

            # get trait object by id
            else:
                trait_obj: Trait = get_sql_session().query(Trait).filter(Trait.id == trait_new.get('id')).first()
                if not trait_obj:
                    throw_exception(f"Can't find trait in db although it has an id: {trait_new.get('id')}")

            # update existing trait's link to taxon (this is where the status attribute lies)
            if trait_obj:
                links_existing = [l for l in trait_obj.taxon_to_trait_associations if l.taxon == taxon]
                if links_existing:
                    links_existing[0].status = trait_new.get('status')
                else:
                    # trait exists, but is not assigned the taxon; create that link
                    link = TaxonToTraitAssociation(
                            taxon=taxon,
                            trait=trait_obj,
                            status=trait_new.get('status'))
                    get_sql_session().add(link)
                    # taxon.taxon_to_trait_associations.append(trait_obj)  # commit in calling method

            # altogether new trait
            else:
                logger.info(f"Creating new trait in db for category {category_obj.category_name}: {trait_new.get('trait')}")
                trait_obj = Trait(
                        trait=trait_new.get('trait'),
                        trait_category=category_obj
                        )
                link = TaxonToTraitAssociation(taxon=taxon,
                                               trait=trait_obj,
                                               status=trait_new.get('status'))
                get_sql_session().add_all([trait_obj, link])

            # collect traits themselves for identifying deleted links later
            new_trait_obj_list.append(trait_obj)

    # remove deleted traits from taxon links
    for link in taxon.taxon_to_trait_associations:
        if link.trait not in new_trait_obj_list:
            logger.info(f"Deleting trait for taxon {taxon.name}: {link.trait.trait}")
            get_sql_session().delete(link)
