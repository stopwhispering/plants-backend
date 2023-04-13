from __future__ import annotations

from typing import TYPE_CHECKING

from plants.shared.proposal_schemas import BTaxonTreeNode

if TYPE_CHECKING:
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.taxon.models import Taxon
    from plants.modules.taxon.taxon_dal import TaxonDAL


def _insert_into_taxon_tree(
    taxon_tree: list[BTaxonTreeNode], taxon: Taxon, plant_ids: list[int]
) -> None:
    family_node: BTaxonTreeNode | None = next(
        (node for node in taxon_tree if node.key == taxon.family), None
    )
    if not family_node:
        family_node = BTaxonTreeNode(
            key=taxon.family,
            level=0,
            count=0,
            nodes=[],
        )
        taxon_tree.append(family_node)

    genus_node: BTaxonTreeNode | None = next(
        (node for node in family_node.nodes if node.key == taxon.genus), None
    )
    if not genus_node:
        genus_node = BTaxonTreeNode(
            key=taxon.genus,
            level=1,
            count=0,
            nodes=[],
        )
        family_node.nodes.append(genus_node)

    # custom taxa might not have a species but a name
    species_name: str = taxon.species or taxon.name
    species_leaf: BTaxonTreeNode | None = next(
        (node for node in genus_node.nodes if node.key == species_name), None
    )
    if not species_leaf:
        species_leaf = BTaxonTreeNode(
            key=species_name,
            level=2,
            count=0,
            plant_ids=[],
        )
        genus_node.nodes.append(species_leaf)

    # we might have multiple taxon ids for that species (e.g. varieties)
    species_leaf.plant_ids.extend(plant_ids)

    genus_node.count += len(plant_ids)
    family_node.count += len(plant_ids)
    species_leaf.count += len(plant_ids)


async def _create_node_for_plants_without_taxon(plant_dal: PlantDAL) -> BTaxonTreeNode | None:
    plant_ids_empty = await plant_dal.fetch_plants_ids_without_taxon()
    count_empty = len(plant_ids_empty)
    if count_empty:
        node_empty_species = BTaxonTreeNode(
            key="",
            level=2,
            count=count_empty,
            plant_ids=plant_ids_empty,
        )
        node_empty_genus = BTaxonTreeNode(
            key="",
            level=1,
            count=count_empty,
            nodes=[node_empty_species],
        )
        return BTaxonTreeNode(
            key="",
            level=0,
            count=count_empty,
            nodes=[node_empty_genus],
        )
    return None


async def build_taxon_tree(taxon_dal: TaxonDAL, plant_dal: PlantDAL) -> list[BTaxonTreeNode]:
    """Build up taxon tree from distinct families, genus, and species that are assigned at least one
    plant."""
    # get sorted distinct families, genera, and species with list of plant ids each
    taxa_with_plant_ids = await taxon_dal.fetch_taxa_with_plant_ids()

    # build up tree
    tree: list[BTaxonTreeNode] = []

    for taxon, plant_ids in taxa_with_plant_ids:
        _insert_into_taxon_tree(tree, taxon, plant_ids)

    # add empty family to allow for selecting plants with no taxon assigned
    family_node_no_taxon_assigned = await _create_node_for_plants_without_taxon(plant_dal)
    if family_node_no_taxon_assigned:
        tree.append(family_node_no_taxon_assigned)

    return tree
