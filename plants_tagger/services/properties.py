# import logging

from flask_2_ui5_py import throw_exception
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.taxon_models import Taxon
from plants_tagger.models.plant_models import Plant
from plants_tagger.models.property_models import PropertyName

# logger = logging.getLogger(__name__)
# RANKS = ['family', 'genus', 'subgen', 'species', 'subsp', 'taxon_id']


def get_or_add_property_name(property_name: str, category_id: int):
    name = get_sql_session().query(PropertyName).filter(
            PropertyName.property_name == property_name,
            PropertyName.category_id == category_id,
            ).first()
    if not name:
        name = PropertyName(property_name=property_name, category_id=category_id)
        get_sql_session().add(name)
        get_sql_session().commit()
    return name


# def get_numerical_rank(rank: str) -> int:
#     if rank == 'family':
#         return 1
#     elif rank == 'genus':
#         return 2
#     elif rank == 'subgen':
#         return 3
#     elif rank == 'species':
#         return 4
#     elif rank == 'subsp':
#         return 5
#     elif rank == 'taxon_id':
#         return 6


# def get_property_value_taxon(named_property_name_id, level, rank):
#     """return named property by taxon rank and property name"""
#     named_properties = get_sql_session().query(PropertyValueTaxon).filter(
#             PropertyValueTaxon.family == level['family'],
#             PropertyValueTaxon.genus == level['genus'],
#             PropertyValueTaxon.subgen == level['subgen'],
#             PropertyValueTaxon.species == level['species'],
#             PropertyValueTaxon.subsp == level['subsp'],
#             PropertyValueTaxon.taxon_id == level['taxon_id'],
#             PropertyValueTaxon.property_name_id == named_property_name_id,
#             PropertyValueTaxon.rank == rank).all()
#     if len(named_properties) > 1:
#         throw_exception(f'Technical Exception: Two NamedProperty entries for the same key. Rank: {rank}',
#                         MessageType.ERROR,
#                         str(level))
#     elif named_properties:
#         return named_properties[0]
#     else:
#         return None


# def get_named_properties(rank_filters, rank) -> [PropertyValueTaxon]:
#     """return all named properties by taxon rank"""
#     q = get_sql_session().query(PropertyValueTaxon).filter(PropertyValueTaxon.rank == rank)
#     for rank_filter in rank_filters:
#         col = getattr(PropertyValueTaxon, rank_filter['rank'], None)
#         if not col:
#             throw_exception('Rank not found: ' + rank_filter['rank'])
#         q = q.filter(col == rank_filter['value'])
#     named_properties = q.all()
#     if named_properties:
#         return named_properties
#     else:
#         return []


# def add_property_value_taxon(property_name: PropertyName, property_value_new: str, rank: str, taxon: Taxon):
#     """generate a named property for a taxon on any level"""
#     add_list = []
#     r = get_numerical_rank(rank)
#     level = {
#         'family':  taxon.family if r >= 1 else None,
#         'genus':   taxon.genus if r >= 2 else None,
#         'subgen':  taxon.subgen if r >= 3 else None,
#         'species': taxon.species if r >= 4 else None,
#         'subsp':   taxon.subsp if r >= 5 else None,
#         'taxon_id':  taxon.id if r == 6 else None  # if taxon.is_custom else None
#         }
#
#     property_value = get_property_value_taxon(property_name.id, level, rank)
#     if not property_value:
#         property_value = PropertyValueTaxon(property_name_id=property_name.id)
#         add_list.append(property_value)
#
#     for t, value in level.items():
#         setattr(property_value, t, value)
#
#     property_value.property_value = property_value_new
#     property_value.rank = rank
#
#     if add_list:
#         get_sql_session().add_all(add_list)
#
#     get_sql_session().commit()


# def get_property_value_plant(property_name: PropertyName, plant: Plant):
#     """return named property by taxon rank and property name"""
#     named_properties = get_sql_session().query(PropertyValuePlant).filter(
#             PropertyValuePlant.property_name == property_name,
#             PropertyValuePlant.plant == plant).all()
#     if len(named_properties) > 1:
#         throw_exception(f'Technical Exception: Two Plant Property entries for the same key: {plant.plant_name} / '
#                         f'{property_name.property_name}',
#                         MessageType.ERROR)
#     elif named_properties:
#         return named_properties[0]
#     else:
#         return None


# def add_property_value_plant(property_name: PropertyName, property_value_new: str, plant: Plant):
#     """generate a named property for a taxon on any level"""
#     add_list = []
#
#     property_value = get_property_value_plant(property_name, plant)
#     if not property_value:
#         property_value = PropertyValuePlant(property_name=property_name,
#                                             plant=plant)
#         add_list.append(property_value)
#
#     property_value.property_value = property_value_new
#
#     if add_list:
#         get_sql_session().add_all(add_list)
#
#     get_sql_session().commit()


# def get_taxon_properties_incl_upper_taxa(taxon: Taxon) -> [PropertyValueTaxon]:
#     """for a plant's taxon, get the property values; get it from highest taxon in
#     hierarchy, override with properties from lower taxa; consider custom species as well"""
#     taxon_properties = []
#     rank_filters = []
#     # iterate over the ranks, from family to custom species, and collect their properties
#     for rank in RANKS:
#         rank_value = getattr(taxon, rank, None)
#         if not rank_value:
#             continue
#         rank_filters.append({'rank': rank,
#                              'value': rank_value})
#         taxon_properties.extend(get_named_properties(rank_filters, rank))
#     return taxon_properties


def get_properties_for_plant_by_category(plant_name: str):
    """return all valid properties for supplied plant; add plant-specific information"""
    plant = get_sql_session().query(Plant).filter(Plant.plant_name == plant_name).first()
    if not plant:
        throw_exception('Plant not found in Database.')

    property_values = plant.property_values_plant
    return assemble_property_values_by_categories(property_values)


def assemble_property_values_by_categories(property_values):
    """bring property values into structure required by frontend; sort by (1) cat. (2) name (3) value
    supplied with property_values of either class PropetryValueTaxon or PropetryValuePlant"""
    # distinct categories considering both plant and taxon property values
    categories = set([p.property_name.property_category for p in property_values])

    # merge plant and taxon property values, sort by categories
    category_collection = []
    for c in categories:

        # get distinct property names
        category = {'property_category': c.category_name,
                    'property_category_id': c.id,
                    'property_names':    []}
        category_collection.append(category)

        values_category = [p for p in property_values if p.property_name.property_category == c]
        names_category = set([v.property_name for v in values_category])

        # add the property name values for current category
        for n in names_category:
            name = {'property_name': n.property_name,
                    'property_name_id': n.id}
            category['property_names'].append(name)

            # distinguish between plant property values and taxon property values by orm class name
            # not required anymore, could be simplified here
            values_name = [p for p in values_category if p.property_name == n]
            for v in values_name:
                # key = 'property_value_plant' if hasattr(v, 'plant') else 'property_value_taxon'
                name['property_value'] = v.property_value
                # name['property_value_id'] = v.id
                # todo: make sure there's only one property value for both plant and taxon in extensions

    return category_collection


def get_properties_for_taxon_by_category(taxon_id: int):
    """return all valid properties for supplied taxon"""
    taxon = get_sql_session().query(Taxon).filter(Taxon.id == taxon_id).first()
    if not taxon:
        throw_exception(f'Taxon {taxon_id} not found in Database.')

    # get property values for both plant and its taxon
    # todo remove upper taxa part
    # property_values: [PropertyValueTaxon] = get_taxon_properties_incl_upper_taxa(taxon)

    property_values = taxon.property_values_taxon
    return assemble_property_values_by_categories(property_values)
