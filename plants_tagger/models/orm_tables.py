from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.sqlite import INTEGER, TEXT, BOOLEAN, TIMESTAMP, DATE, CHAR
import logging
from sqlalchemy import inspect
from sqlalchemy.orm import relationship

from plants_tagger.config import TRAIT_CATEGORIES
from plants_tagger.models import init_sqlalchemy_engine, get_sql_session
from plants_tagger.models.orm_util import Base

logger = logging.getLogger(__name__)


def object_as_dict(obj):
    # converts an orm object into a dict
    # does not include objects from relationships and _sa_instance_state
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}


def objects_list_to_dict(obj_list) -> dict:
    # converts a list of orm objects into a dict mapping id to dict
    # does not include objects from relationships and _sa_instance_state
    dict_main = {}
    for obj in obj_list:
        dict_sub = {c.key: getattr(obj, c.key)
                    for c in inspect(obj).mapper.column_attrs}
        # get primary key tuple; if only one element, set that as dict key, otherwise the tuple
        primary_key_tuple = inspect(obj).mapper.primary_key_from_instance(obj)
        primary_key = primary_key_tuple[0] if len(primary_key_tuple) == 1 else primary_key_tuple
        dict_main[primary_key] = dict_sub

    return dict_main


class Plant(Base):
    """my plants"""
    __tablename__ = 'plants'
    plant_name = Column(CHAR(60), primary_key=True, nullable=False)  # unique even if we switched to id's later
    # species = Column(CHAR(60), ForeignKey('botany.species'))
    species = Column(CHAR(60))
    count = Column(INTEGER)
    active = Column(BOOLEAN)  # plant may be inactive (e.g. separated) but not flagged dead; inactive ~ untraceable
    # dead = Column(BOOLEAN)
    generation_date = Column(DATE)
    generation_type = Column(CHAR(60))
    generation_notes = Column(CHAR(120))
    mother_plant = Column(CHAR(60), ForeignKey('plants.plant_name'))
    generation_origin = Column(CHAR(60))
    plant_notes = Column(TEXT)
    filename_previewimage = Column(CHAR(240))  # original filename of the image that is set as preview image
    hide = Column(BOOLEAN)
    last_update = Column(TIMESTAMP, nullable=False)

    # plant to taxon: n:1
    taxon_id = Column(INTEGER, ForeignKey('taxon.id'))
    taxon = relationship("Taxon", back_populates="plants")

    # plant to tag: 1:n
    tags = relationship("Tag", back_populates="plant")

    # plant to event: 1:n
    events = relationship("Event", back_populates="plant")


class Tag(Base):
    """tags displayed in master view and created/deleted in details view"""
    __tablename__ = 'tags'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    text = Column(CHAR(20))
    icon = Column(CHAR(30))  # full uri, e.g. 'sap-icon://hint'
    state = Column(CHAR(11))  # Error, Information, None, Success, Warning
    last_update = Column(TIMESTAMP)
    # tag to plant: n:1
    plant_name = Column(CHAR(60), ForeignKey('plants.plant_name'))
    plant = relationship("Plant", back_populates="tags")


class Distribution(Base):
    """geographic distribution"""
    __tablename__ = 'distribution'

    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    name = Column(CHAR(40))
    establishment = Column(CHAR(15))
    feature_id = Column(CHAR(5))
    tdwg_code = Column(CHAR(10))
    tdwg_level = Column(INTEGER)

    taxon_id = Column(INTEGER, ForeignKey('taxon.id'))
    taxon = relationship("Taxon", back_populates="distribution")


class Taxon(Base):
    """botanical details"""
    __tablename__ = 'taxon'

    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    name = Column(CHAR(100))
    is_custom = Column(BOOLEAN)
    subsp = Column(CHAR(100))
    species = Column(CHAR(100))
    subgen = Column(CHAR(100))
    genus = Column(CHAR(100))
    family = Column(CHAR(100))
    phylum = Column(CHAR(100))
    kingdom = Column(CHAR(100))
    rank = Column(CHAR(30))
    taxonomic_status = Column(CHAR(100))
    name_published_in_year = Column(INTEGER)
    synonym = Column(BOOLEAN)
    fq_id = Column(CHAR(50))
    authors = Column(CHAR(100))
    basionym = Column(CHAR(100))
    synonyms_concat = Column(CHAR(200))
    distribution_concat = Column(CHAR(200))
    hybrid = Column(BOOLEAN)
    hybridgenus = Column(BOOLEAN)
    gbif_id = Column(INTEGER)  # Global Biodiversity Information Facility
    powo_id = Column(CHAR(50))
    custom_notes = Column(TEXT)  # may be updated on web frontend

    plants = relationship("Plant", back_populates="taxon")
    distribution = relationship("Distribution", back_populates="taxon")

    # 1:n relationship to the taxon/traits link table
    traits = relationship(
            "Trait",
            secondary='taxon_to_trait_association'
            )
    taxon_to_trait_associations = relationship("TaxonToTraitAssociation", back_populates="taxon")

# soil_to_component_association_table = Table('soil_to_component_association',
#                                             Base.metadata,
#                                             Column('soil_id', INTEGER, ForeignKey('soil.id')),
#                                             Column('soil_component_id', INTEGER, ForeignKey('soil_component.id')),
#                                             Column('portion', CHAR(20))
#                                             )


class Soil(Base):
    __tablename__ = "soil"
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    soil_name = Column(CHAR(100))
    components = relationship(
            "SoilComponent",
            secondary='soil_to_component_association'
            )

    # 1:n relationship to events (no need for bidirectional relationship)
    events = relationship("Event", back_populates="soil")

    # 1:n relationship to the soil/components link table
    soil_to_component_associations = relationship("SoilToComponentAssociation", back_populates="soil")


class SoilComponent(Base):
    __tablename__ = "soil_component"
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    component_name = Column(CHAR(100))
    soils = relationship(
            Soil,
            secondary='soil_to_component_association'
            )

    # 1:n relationship to the soil/components link table
    soil_to_component_associations = relationship("SoilToComponentAssociation", back_populates="soil_component")


class SoilToComponentAssociation(Base):
    __tablename__ = 'soil_to_component_association'
    soil_id = Column(INTEGER, ForeignKey('soil.id'), primary_key=True)
    soil_component_id = Column(INTEGER, ForeignKey('soil_component.id'), primary_key=True)
    portion = Column(CHAR(20))

    # #n:1 relationship to the soil table and to the soil component table
    soil = relationship('Soil', back_populates="soil_to_component_associations")
    soil_component = relationship('SoilComponent', back_populates="soil_to_component_associations")


class Pot(Base):
    __tablename__ = "pot"
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    material = Column(CHAR(50))
    shape_top = Column(CHAR(20))  # oval, square, circle
    shape_side = Column(CHAR(20))   # flat, very flat, high, very high
    diameter_width = Column(INTEGER)  # in mm
    # pot_notes = Column(TEXT)

    # 1:n relationship to events
    events = relationship("Event", back_populates="pot")


class Observation(Base):
    """formerly: Measurement"""
    __tablename__ = 'observation'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    # plant_name = Column(CHAR(60), nullable=False)
    diseases = Column(TEXT)
    stem_max_diameter = Column(INTEGER)  # stem or caudex (max) in mm
    height = Column(INTEGER)  # in mm
    # location = Column(CHAR(30))
    observation_notes = Column(TEXT)

    # 1:1 relationship to event
    event = relationship("Event", back_populates="observation", uselist=False)


class Image(Base):
    """image paths"""
    # images themselves are stored in file system and their information in exif tags
    # this table is only used to link events to images
    # todo: helper method to find a missing image in other subdirectories (in case of moving files manually)
    __tablename__ = 'image'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    relative_path = Column(CHAR(240))  # relative path to the original image file incl. file name  # pseudo-key

    # 1:n relationship to the image/event link table
    events = relationship(
            "Event",
            secondary='image_to_event_association'
            )
    image_to_event_associations = relationship("ImageToEventAssociation", back_populates="image")


class ImageToEventAssociation(Base):
    __tablename__ = 'image_to_event_association'
    image_id = Column(INTEGER, ForeignKey('image.id'), primary_key=True)
    event_id = Column(INTEGER, ForeignKey('event.id'), primary_key=True)

    image = relationship('Image', back_populates='image_to_event_associations')
    event = relationship('Event', back_populates='image_to_event_associations')


class Event(Base):
    """events"""
    __tablename__ = 'event'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    date = Column(CHAR(12), nullable=False)  # e.g. 201912241645 or 201903
    # action = Column(CHAR(60), nullable=False)  # purchase, measurement,  seeding, repotting (enum)
    icon = Column(CHAR(30))  # full uri, e.g. 'sap-icon://hint'
    event_notes = Column(TEXT)

    # 1:1 relationship to observation (joins usually from event to observation, not the other way around)
    observation_id = Column(INTEGER, ForeignKey('observation.id'))
    observation = relationship("Observation", back_populates="event")

    # n:1 relationship to pot, bi-directional
    pot_id = Column(INTEGER, ForeignKey('pot.id'))
    pot_event_type = Column(CHAR(15))  # Repotting, Status
    pot = relationship("Pot", back_populates="events")

    # n:1 relationship to soil, bi-directional
    soil_id = Column(INTEGER, ForeignKey('soil.id'))
    soil_event_type = Column(CHAR(15))  # Changing Soil, Status
    soil = relationship("Soil", back_populates="events")

    # event to plant: n:1, bi-directional
    plant_name = Column(CHAR(60), ForeignKey('plants.plant_name'), nullable=False)
    plant = relationship("Plant", back_populates="events")

    # 1:n relationship to the image/event link table
    images = relationship(
            "Image",
            secondary='image_to_event_association'
            )
    image_to_event_associations = relationship("ImageToEventAssociation", back_populates="event")


class TaxonToTraitAssociation(Base):
    __tablename__ = 'taxon_to_trait_association'
    taxon_id = Column(INTEGER, ForeignKey('taxon.id'), primary_key=True)
    trait_id = Column(INTEGER, ForeignKey('trait.id'), primary_key=True)
    # observed = Column(BOOLEAN)
    status = Column(CHAR(20))

    taxon = relationship('Taxon', back_populates='taxon_to_trait_associations')
    trait = relationship('Trait', back_populates='taxon_to_trait_associations')


class Trait(Base):
    """traits"""
    __tablename__ = 'trait'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    trait = Column(CHAR(240))

    # 1:n relationship to the taxon/traits link table
    taxa = relationship(
            "Taxon",
            secondary='taxon_to_trait_association'
            )
    taxon_to_trait_associations = relationship("TaxonToTraitAssociation", back_populates="trait")

    # trait to trait category: n:1
    trait_category_id = Column(INTEGER, ForeignKey('trait_category.id'))
    trait_category = relationship("TraitCategory", back_populates="traits")


class TraitCategory(Base):
    """trait categories"""
    __tablename__ = 'trait_category'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    category_name = Column(CHAR(80))
    sort_flag = Column(INTEGER)

    traits = relationship("Trait", back_populates="trait_category")


logging.getLogger(__name__).info('Initializing SQLAlchemy Engine')
init_sqlalchemy_engine()

# add Trait Categories if not existing
for t in TRAIT_CATEGORIES:
    trait_category = get_sql_session().query(TraitCategory).filter(TraitCategory.category_name == t).first()
    if not trait_category:
        logger.info(f'Inserting missing trait category into db: {t}')
        trait_category = TraitCategory(category_name=t)
        get_sql_session().add(trait_category)
get_sql_session().commit()
