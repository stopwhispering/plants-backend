import time

from sqlalchemy.orm import subqueryload

from plants.dependencies import get_db
from plants.extensions.db import engine
from plants.extensions.orm import init_orm
from plants.modules.event.models import Event
from plants.modules.image.models import ImageKeyword, Image, ImageToTaxonAssociation
# from plants.models.event_models import Soil, Pot, Observation, Event
# from plants.models.history_model import History
# from plants.models.image_models import ImageKeyword, ImageToPlantAssociation, Image, ImageToEventAssociation, \
#     ImageToTaxonAssociation
from plants.modules.plant.models import Plant
from plants.modules.property.models import PropertyCategory
from plants.modules.taxon.models import Taxon
from plants.modules.image.services import _to_response_image
from plants.shared.message_services import get_message
from plants.shared.message_schemas import BMessageType
from plants.modules.event.schemas import BResultsEventResource
from plants.modules.image.schemas import FBImages, BResultsImageResource
from plants.modules.plant.schemas import BResultsPlants
from plants.modules.property.schemas import BResultsPropertyNames
from plants.shared.proposal_schemas import BResultsProposals, FProposalEntity

# from plants.models.pollination_models import Florescence, Pollination
# from plants.models.property_models import PropertyCategory, PropertyName, PropertyValue
# from plants.models.tag_models import Tag
# from plants.models.taxon_models import Distribution, Taxon, TaxonOccurrenceImage, TaxonToOccurrenceAssociation

init_orm(engine=engine)
db = next(get_db())


class catchtime:
    """pseudo-context-manager to measure time"""
    def __enter__(self):
        self.start_absolute = time.time()
        self.start_perf = time.perf_counter()
        return self

    def __exit__(self, type, value, traceback):  # noqa
        self.end_absolute = time.time() - self.start_absolute
        self.end_perf = time.perf_counter() - self.start_perf
        # self.readout = f'Time: {self.time:.3f} seconds'
        print(f'Absolute time: {self.end_absolute:.4f} seconds')
        print(f'Perf time: {self.end_perf:.4f} seconds')


def plants_subqueryload():
    query = db.query(Plant)
    # query = query.filter((Plant.hide.is_(False)) | (Plant.hide.is_(None)))
    query = query.filter(Plant.deleted.is_(False))

    # early-load all relationship tables for Plant model relevant for PResultsPlants
    query = query.options(
        subqueryload(Plant.parent_plant),
        subqueryload(Plant.parent_plant_pollen),

        subqueryload(Plant.tags),
        subqueryload(Plant.same_taxon_plants),
        subqueryload(Plant.sibling_plants),

        subqueryload(Plant.descendant_plants),
        subqueryload(Plant.descendant_plants_pollen),
        # subqueryload(Plant.descendant_plants_all),  # property

        subqueryload(Plant.taxon),
        # subqueryload(Plant.taxon_authors),  # property

        subqueryload(Plant.events),
        # subqueryload(Plant.current_soil),  # property

        subqueryload(Plant.images),
        # subqueryload(Plant.latest_image),  # property

        # subqueryload(Plant.property_values_plant),  # not required
        # subqueryload(Plant.image_to_plant_associations),  # not required
        # subqueryload(Plant.florescences),  # not required
    )
    plants_obj = query.all()
    results = {'action':           'Get plants',
               'resource':         'PlantResource',
               'message':          get_message(f"Loaded {len(plants_obj)} plants from database."),
               'PlantsCollection': plants_obj}
    BResultsPlants.parse_obj(results)


def plants_no_subqueryload():
    query = db.query(Plant)
    # query = query.filter((Plant.hide.is_(False)) | (Plant.hide.is_(None)))
    query = query.filter(Plant.deleted.is_(False))
    plants_obj = query.all()
    results = {'action':           'Get plants',
               'resource':         'PlantResource',
               'message':          get_message(f"Loaded {len(plants_obj)} plants from database."),
               'PlantsCollection': plants_obj}
    BResultsPlants.parse_obj(results)


def keyword_proposals():
    # /api/proposals/KeywordProposals
    # 0.01095438003540039 seconds
    keyword_tuples = db.query(ImageKeyword.keyword).distinct().all()
    keywords_set = {k[0] for k in keyword_tuples}
    keywords_collection = [{'keyword': keyword} for keyword in keywords_set]
    results = {'KeywordsCollection': keywords_collection}
    results.update({'action': 'Get',
                    'resource': 'ProposalResource',
                    'message': get_message(f'Receiving proposal values for entity {FProposalEntity.KEYWORD} from backend.')})
    BResultsProposals.parse_obj(results)


def events_for_plant():
    #   /api/events/495
    # 0.0753018856048584 seconds
    results = []
    plant_id = 495
    event_objs = Event.get_events_by_plant_id(plant_id, db)
    for event_obj in event_objs:
        results.append(event_obj.as_dict())

    results = {'events': results,
               'message': get_message(f'Receiving {len(results)} events for {Plant.get_plant_name_by_plant_id(plant_id, db)}.',
                                      message_type=BMessageType.DEBUG)}
    BResultsEventResource.parse_obj(results)


def images_for_plant():
    # /api/plants/495/images/
    # 0.05376739997882396 seconds
    plant_id = 495
    plant = Plant.get_plant_by_plant_id(plant_id, db=db, raise_exception=True)
    photo_files_ext = [_to_response_image(image) for image in plant.images]
    FBImages.parse_obj(photo_files_ext)


def taxa():
    # /api/taxa/
    taxa: list[Taxon] = db.query(Taxon).options(  # noqa
        subqueryload(Taxon.distribution),
        subqueryload(Taxon.occurrence_images),
        subqueryload(Taxon.images),

        # subqueryload(Taxon.plants),  # not required
        # subqueryload(Taxon.property_values_taxon),  # not required

        subqueryload(Taxon.image_to_taxon_associations)
        .subqueryload(ImageToTaxonAssociation.image),
    ).all()
    taxon_dict = {}
    for taxon in taxa:
        taxon_dict[taxon.id] = taxon.as_dict()
        # images
        taxon_dict[taxon.id]['images'] = []
        if taxon.images:
            for link_obj in taxon.image_to_taxon_associations:
                image_obj: Image = link_obj.image
                taxon_dict[taxon.id]['images'].append({'id': image_obj.id,
                                                       'filename': image_obj.filename,
                                                       'description': link_obj.description})

        # distribution codes according to WGSRPD (level 3)
        taxon_dict[taxon.id]['distribution'] = {'native': [],
                                                'introduced': []}
        for distribution_obj in taxon.distribution:
            if distribution_obj.establishment == 'Native':
                taxon_dict[taxon.id]['distribution']['native'].append(distribution_obj.tdwg_code)
            elif distribution_obj.establishment == 'Introduced':
                taxon_dict[taxon.id]['distribution']['introduced'].append(distribution_obj.tdwg_code)

        # occurence images
        taxon_dict[taxon.id]['occurrenceImages'] = [o.as_dict() for o in taxon.occurrence_images]

    message = f'Received {len(taxon_dict)} taxa from database.'
    results = {'action': 'Get taxa',
               'resource': 'TaxonResource',
               'message': get_message(message),
               'TaxaDict': taxon_dict}
    BResultsGetTaxa.parse_obj(results)


def untagged():
    # /api/images/untagged/
    # 0.016927480697631836 seconds
    untagged_images = db.query(Image).filter(~Image.plants.any()).all()  # noqa
    images_ext = [_to_response_image(image) for image in untagged_images]
    results = {'ImagesCollection': images_ext,
               'message': get_message('Loaded images from backend.',
                                      description=f'Count: {len(images_ext)}')
               }
    BResultsImageResource.parse_obj(results)


def property_names():
    # /api/property_names/
    # 0.0922 seconds
    query = db.query(PropertyCategory).options(subqueryload(PropertyCategory.property_names))
    category_obj = query.all()
    categories = {}
    for cat in category_obj:
        cat: PropertyCategory
        categories[cat.category_name] = [{'property_name':    p.property_name,
                                          'property_name_id': p.id,
                                          'countPlants':      len(p.property_values)
                                          } for p in cat.property_names]

    results = {
        'action':                         'Get',
        'resource':                       'PropertyNameResource',
        'propertiesAvailablePerCategory': categories,
        'message':                        get_message(f"Receiving Property Names from database.")
        }

    BResultsPropertyNames.parse_obj(results)


# print(config.db_type)
functions = [
    # plants_no_subqueryload,
    # plants_subqueryload,
    # keyword_proposals,
    # events_for_plant,
    # images_for_plant,
    # taxa,
    # untagged,
    property_names,
]
for f in functions:
    with catchtime():
        f()
    db.expire_all()
    db.close()
