from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.taxon.taxon_dal import TaxonDAL


class FamilyNodeDict(TypedDict):
    key: str
    nodes: list[GenusNodeDict]
    level: int
    count: int


class GenusNodeDict(TypedDict):
    key: str
    nodes: list[SpeciesLeafDict]
    level: int
    count: int


class SpeciesLeafDict(TypedDict):
    key: str
    level: int
    plant_ids: list[int]
    count: int


async def build_taxon_tree(
    taxon_dal: TaxonDAL, plant_dal: PlantDAL
) -> list[FamilyNodeDict]:
    """Build up taxon tree from distinct families, genus, and species that are assigned
    at least one plant."""
    # todo optimize sql performance
    # get distinct families, genus, and species (as list of four-element-tuples); sort
    dist_tuples: list[
        tuple[str, str, str | None, int]
    ] = await taxon_dal.get_distinct_species_as_tuples()

    # build up tree
    tree = []
    previous_family = None
    previous_genus = None
    previous_species = None

    family_node: FamilyNodeDict = {"key": "", "nodes": [], "level": 0, "count": 0}
    genus_node: GenusNodeDict = {"key": "", "nodes": [], "level": 1, "count": 0}
    species_leaf: SpeciesLeafDict = {"key": "", "plant_ids": [], "level": 2, "count": 0}

    for current_family, current_genus, current_species, current_taxon_id in dist_tuples:
        # get family node
        if current_family != previous_family:
            new_family = True
            family_node = {
                "key": current_family,
                "nodes": [],
                "level": 0,
                "count": 0,
            }
            tree.append(family_node)
        else:
            new_family = False

        # get genus node
        if (current_genus != previous_genus) or new_family:
            new_genus = True
            genus_node = {
                "key": current_genus,
                "nodes": [],
                "level": 1,
                "count": 0,
            }
            family_node["nodes"].append(genus_node)
        else:
            new_genus = False

        # create species leaf
        current_species_: str = current_species or "[Custom]"
        if (current_species != previous_species) or new_genus:
            species_leaf = {
                "key": current_species_,
                "level": 2,
                "plant_ids": [],
                "count": 0,
            }
            genus_node["nodes"].append(species_leaf)

        # we might have multiple taxon ids for that species (e.g. varieties), for
        # each of them, get plant ids
        # todo: do a join at the top so we don't need that lookup here
        plant_ids_tuple = await plant_dal.get_plant_ids_by_taxon_id(
            taxon_id=current_taxon_id, eager_load=False
        )  # load no relationships
        species_leaf["plant_ids"].extend(list(plant_ids_tuple))

        genus_node["count"] += (plants_current_taxon := len(plant_ids_tuple))
        family_node["count"] += plants_current_taxon
        species_leaf["count"] += plants_current_taxon

        previous_family = current_family
        previous_genus = current_genus
        previous_species = current_species_

    # add empty family to allow for selecting plants with no taxon assigned
    count_empty = await plant_dal.get_count_plants_without_taxon()
    if count_empty:
        plant_ids_empty = await plant_dal.get_plants_ids_without_taxon()
        node_empty_species: SpeciesLeafDict = {
            "key": "",
            "level": 2,
            "count": count_empty,
            "plant_ids": plant_ids_empty,
        }
        node_empty_genus: GenusNodeDict = {
            "key": "",
            "level": 1,
            "count": count_empty,
            "nodes": [node_empty_species],
        }
        node_empty_family: FamilyNodeDict = {
            "key": "",
            "level": 0,
            "count": count_empty,
            "nodes": [node_empty_genus],
        }
        tree.append(node_empty_family)
    return tree
