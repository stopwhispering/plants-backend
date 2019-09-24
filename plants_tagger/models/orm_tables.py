from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.sqlite import INTEGER, TEXT, BOOLEAN, TIMESTAMP, DATE, CHAR
import logging
from sqlalchemy import inspect
from sqlalchemy.orm import relationship

from plants_tagger.models import init_sqlalchemy_engine
from plants_tagger.models.orm_util import Base


def object_as_dict(obj):
    # converts an orm object into a dict
    # does not include objects from relationships and _sa_instance_state
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}


class Plant(Base):
    """my plants"""
    __tablename__ = 'plants'
    plant_name = Column(CHAR(60), primary_key=True, nullable=False)
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

#
# class Measurement(Base):
#     """assessments"""
#     __tablename__ = 'measurement'
#     plant_name = Column(CHAR(60), primary_key=True, nullable=False)
#     measurement_date = Column(DATE, primary_key=True, nullable=False)
#     repot_rating = Column(INTEGER)  # 0 (no repotting required) to 5 (repotting urgently required)
#     # stem_outset_diameter = Column(INTEGER)  # stem or caudex (outset) in mm
#     stem_max_diameter = Column(INTEGER)  # stem or caudex (max) in mm
#     height = Column(INTEGER)  # in mm
#     pot_width_above = Column(INTEGER)  # in mm
#     # pot_width_below = Column(INTEGER)  # in mm
#     pot_circular = Column(BOOLEAN)  # false = quadratic
#     # pot_height = Column(INTEGER)  # in mm
#     pot_material = Column(CHAR(50))
#     soil = Column(CHAR(200))
#     notes = Column(TEXT)


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
    shape_top = Column(CHAR(20))  # oval, square, circle  # todo enum
    shape_side = Column(CHAR(20))   # flat, very flat, high, very high #todo enum
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


logging.getLogger(__name__).info('Initializing SQLAlchemy Engine')
init_sqlalchemy_engine()
