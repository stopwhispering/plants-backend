from sqlalchemy import Column, CHAR, INTEGER, BOOLEAN, ForeignKey, TEXT, TIMESTAMP, Enum
from sqlalchemy.dialects.sqlite import DATE
from sqlalchemy.orm import relationship

from plants_tagger.extensions.orm import Base


class Plant(Base):
    """my plants"""
    __tablename__ = 'plants'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    plant_name = Column(CHAR(60), unique=True, nullable=False)
    # species = Column(CHAR(60))

    field_number = Column(CHAR(20))
    geographic_origin = Column(CHAR(100))
    nursery_source = Column(CHAR(100))
    # propagation_type = Column(CHAR(20))  # vegetative or generative
    propagation_type = Column(Enum("vegetative", "generative", "unknown", name="propagation_type_enum"))

    count = Column(INTEGER)
    active = Column(BOOLEAN)  # plant may be inactive (e.g. separated) but not flagged dead; inactive ~ untraceable
    # dead = Column(BOOLEAN)
    generation_date = Column(DATE)
    generation_type = Column(CHAR(60))
    generation_notes = Column(CHAR(120))
    # mother_plant = Column(CHAR(60), ForeignKey('plants.plant_name'))
    mother_plant_id = Column(INTEGER, ForeignKey('plants.id'))
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

    # plant to plant property values: 1:n
    property_values_plant = relationship("PropertyValuePlant", back_populates="plant")


class Tag(Base):
    """tags displayed in master view and created/deleted in details view"""
    __tablename__ = 'tags'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    text = Column(CHAR(20))
    icon = Column(CHAR(30))  # full uri, e.g. 'sap-icon://hint'
    state = Column(CHAR(11))  # Error, Information, None, Success, Warning
    last_update = Column(TIMESTAMP)
    # tag to plant: n:1
    # plant_name = Column(CHAR(60), ForeignKey('plants.plant_name'))
    plant_id = Column(INTEGER, ForeignKey('plants.id'))
    plant = relationship("Plant", back_populates="tags")


# class Tag_tmp(Base):
#     """tags displayed in master view and created/deleted in details view"""
#     __tablename__ = 'tags_tmp'
#     id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
#     text = Column(CHAR(20))
#     icon = Column(CHAR(30))  # full uri, e.g. 'sap-icon://hint'
#     state = Column(CHAR(11))  # Error, Information, None, Success, Warning
#     last_update = Column(TIMESTAMP)
#     # tag to plant: n:1
#     # plant_name = Column(CHAR(60), ForeignKey('plants.plant_name'))
#     plant_id = Column(INTEGER, ForeignKey('plants.id'))
#     # plant = relationship("Plant", back_populates="tags")

# class Plant_tmp(Base):
#     """my plants"""
#     __tablename__ = 'plants_tmp'
#     id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
#     plant_name = Column(CHAR(60), unique=True, nullable=False)
#     # species = Column(CHAR(60))
#
#     field_number = Column(CHAR(20))
#     geographic_origin = Column(CHAR(100))
#     nursery_source = Column(CHAR(100))
#     # propagation_type = Column(CHAR(20))  # vegetative or generative
#     propagation_type = Column(Enum("vegetative", "generative", "unknown", name="propagation_type_enum"))
#
#     count = Column(INTEGER)
#     active = Column(BOOLEAN)  # plant may be inactive (e.g. separated) but not flagged dead; inactive ~ untraceable
#     # dead = Column(BOOLEAN)
#     generation_date = Column(DATE)
#     generation_type = Column(CHAR(60))
#     generation_notes = Column(CHAR(120))
#     # mother_plant = Column(CHAR(60), ForeignKey('plants.plant_name'))
#     mother_plant_id = Column(INTEGER, ForeignKey('plants.id'))
#     generation_origin = Column(CHAR(60))
#     plant_notes = Column(TEXT)
#     filename_previewimage = Column(CHAR(240))  # original filename of the image that is set as preview image
#     hide = Column(BOOLEAN)
#     last_update = Column(TIMESTAMP, nullable=False)
#
#     # plant to taxon: n:1
#     taxon_id = Column(INTEGER, ForeignKey('taxon.id'))
#     # taxon = relationship("Taxon", back_populates="plants")
#
#     # plant to tag: 1:n
#     # tags = relationship("Tag", back_populates="plant")
#
#     # plant to event: 1:n
#     # events = relationship("Event", back_populates="plant")
#
#     # plant to plant property values: 1:n
#     # property_values_plant = relationship("PropertyValuePlant", back_populates="plant")