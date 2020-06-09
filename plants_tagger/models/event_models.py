from sqlalchemy import Column, INTEGER, CHAR, ForeignKey, TEXT
from sqlalchemy.orm import relationship
import logging

from plants_tagger.config import TRAIT_CATEGORIES
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.trait_models import TraitCategory
from plants_tagger.extensions.orm import Base


logger = logging.getLogger(__name__)


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


# class Event_tmp(Base):
#     """events"""
#     __tablename__ = 'event_tmp'
#     id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
#     date = Column(CHAR(12), nullable=False)  # e.g. 201912241645 or 201903
#     # action = Column(CHAR(60), nullable=False)  # purchase, measurement,  seeding, repotting (enum)
#     icon = Column(CHAR(30))  # full uri, e.g. 'sap-icon://hint'
#     event_notes = Column(TEXT)
#
#     # 1:1 relationship to observation (joins usually from event to observation, not the other way around)
#     observation_id = Column(INTEGER, ForeignKey('observation.id'))
#     # observation = relationship("Observation", back_populates="event")
#
#     # n:1 relationship to pot, bi-directional
#     pot_id = Column(INTEGER, ForeignKey('pot.id'))
#     pot_event_type = Column(CHAR(15))  # Repotting, Status
#     # pot = relationship("Pot", back_populates="events")
#
#     # n:1 relationship to soil, bi-directional
#     soil_id = Column(INTEGER, ForeignKey('soil.id'))
#     soil_event_type = Column(CHAR(15))  # Changing Soil, Status
#     # soil = relationship("Soil", back_populates="events")
#
#     # event to plant: n:1, bi-directional
#     # plant_name = Column(CHAR(60), ForeignKey('plants.plant_name'), nullable=False)
#     plant_id = Column(INTEGER, ForeignKey('plants.id'), nullable=False)
#     # plant = relationship("Plant", back_populates="events")
#
#     # 1:n relationship to the image/event link table
#     # images = relationship(
#     #         "Image",
#     #         secondary='image_to_event_association'
#     #         )
#     # image_to_event_associations = relationship("ImageToEventAssociation", back_populates="event")


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
    # plant_name = Column(CHAR(60), ForeignKey('plants.plant_name'), nullable=False)
    plant_id = Column(INTEGER, ForeignKey('plants.id'), nullable=False)
    plant = relationship("Plant", back_populates="events")

    # 1:n relationship to the image/event link table
    images = relationship(
            "Image",
            secondary='image_to_event_association'
            )
    image_to_event_associations = relationship("ImageToEventAssociation", back_populates="event")


def insert_categories():
    # add Trait Categories if not existing upon initializing
    for t in TRAIT_CATEGORIES:
        trait_category = get_sql_session().query(TraitCategory).filter(TraitCategory.category_name == t).first()
        if not trait_category:
            logger.info(f'Inserting missing trait category into db: {t}')
            trait_category = TraitCategory(category_name=t)
            get_sql_session().add(trait_category)
    get_sql_session().commit()
