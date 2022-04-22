from operator import or_, and_
from typing import List
from sqlalchemy.orm import Session

from plants.models.taxon_models import Taxon
from plants.models.plant_models import Plant


def build_taxon_tree(db: Session) -> List:
    # todo optimize sql performance
    # build up an exists filter that we're gonna reuse
    plant_exists_filter = and_(or_(Plant.hide.is_(None), Plant.hide.is_(False)), Plant.active)
    exists_filter = Taxon.plants.any(plant_exists_filter)

    # get distinct families, genus, and species (as list of four-element-tuples); sort
    dist_tuples = db.query(Taxon.family, Taxon.genus, Taxon.species, Taxon.id).filter(
            exists_filter).distinct(
            ).order_by(Taxon.family, Taxon.genus, Taxon.species).all()

    # build up tree
    tree = []
    previous_family = None
    previous_genus = None
    previous_species = None
    family_node = None
    genus_node = None
    species_leaf = None

    for t in dist_tuples:
        # get family node
        if (current_family := t[0]) != previous_family:
            new_family = True
            family_node = {'key':   current_family,
                           'nodes': [],
                           'level': 0,
                           'count': 0}
            tree.append(family_node)
        else:
            new_family = False

        # get genus node
        if ((current_genus := t[1]) != previous_genus) or new_family:
            new_genus = True
            genus_node = {'key':   current_genus,
                          'nodes': [],
                          'level': 1,
                          'count': 0}
            family_node['nodes'].append(genus_node)
        else:
            new_genus = False

        # create species leaf
        current_species = t[2] or '[Custom]'
        if (current_species != previous_species) or new_genus:
            species_leaf = {'key':       current_species,
                            'level':     2,
                            'plant_ids': [],
                            'count':     0}
            genus_node['nodes'].append(species_leaf)

        # we might have multiple taxon ids for that species (e.g. varieties), for each of them, get plant ids
        # todo: do a join at the top so we don't need that lookup here
        plant_ids_tuple = db.query(Plant.id).filter(Plant.taxon_id == t[3], or_(Plant.hide.is_(None),
                                                                                Plant.hide.is_(False)),
                                                    Plant.active.is_(True)).all()
        species_leaf['plant_ids'].extend([t[0] for t in plant_ids_tuple])

        genus_node['count'] += (plants_current_taxon := len(plant_ids_tuple))
        family_node['count'] += plants_current_taxon
        species_leaf['count'] += plants_current_taxon

        previous_family = current_family
        previous_genus = current_genus
        previous_species = current_species

    # add empty family to allow for selecting plants with no taxon assigned
    count_empty = db.query(Plant).filter(and_(plant_exists_filter, Plant.taxon_id.is_(None))).count()
    if count_empty:
        plant_ids_empty_tuples = db.query(Plant.id).filter(and_(plant_exists_filter, Plant.taxon_id.is_(None))).all()
        plant_ids_empty = [t[0] for t in plant_ids_empty_tuples]
        node_empty_species = {'key': '', 'level': 2, 'count': count_empty, 'plant_ids': plant_ids_empty}
        node_empty_genus = {'key': '', 'level': 1, 'count': count_empty, 'nodes': [node_empty_species]}
        node_empty_family = {'key': '', 'level': 0, 'count': count_empty, 'nodes': [node_empty_genus]}
        tree.append(node_empty_family)
    return tree
