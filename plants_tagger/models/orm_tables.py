from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.sqlite import INTEGER, TEXT, BOOLEAN, TIMESTAMP, DATE, CHAR

from plants_tagger.models.orm_util import Base


class Plant(Base):
    """my plants"""
    __tablename__ = 'plants'
    plant_name = Column(CHAR(60), primary_key=True, nullable=False)
    species = Column(CHAR(60), ForeignKey('botany.species'))
    count = Column(INTEGER)
    active = Column(BOOLEAN)  # plant may be inactive (e.g. separated) but not flagged dead; inactive ~ untraceable
    dead = Column(BOOLEAN)
    generation_date = Column(DATE)
    generation_type = Column(CHAR(60))
    generation_notes = Column(CHAR(120))
    mother_plant = Column(CHAR(60), ForeignKey('plants.plant_name'))
    generation_origin = Column(CHAR(60))
    plant_notes = Column(TEXT)
    filename_previewimage = Column(CHAR(240))  # original filename of the image that is set as preview image
    hide = Column(BOOLEAN)
    # image_medium = Column(BLOB)
    last_update = Column(TIMESTAMP, nullable=False)


# class Group(Base):
#     """group of plants"""
#     __tablename__ = 'group'
#     group_id = Column(INTEGER, primary_key=True, nullable=False)
#     plant_name = Column(CHAR(60), ForeignKey('plants.plant_name'), primary_key=True, nullable=True)
#

# class Event(Base):
#     """events"""
#     __tablename__ = 'events'
#     id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
#     plant_name = Column(CHAR(60), ForeignKey('plants.plant_name'))
#     event_type = Column(CHAR(60))
#     event_date = Column(DATE)
#     event_notes = Column(TEXT)
#     substrate = Column(CHAR(120))
#


class Measurement(Base):
    """assessments"""
    __tablename__ = 'measurement'
    plant_name = Column(CHAR(60), primary_key=True, nullable=False)
    measurement_date = Column(DATE, primary_key=True, nullable=False)
    repot_rating = Column(INTEGER)  # 0 (no repotting required) to 5 (repotting urgently required)
    stem_outset_diameter = Column(INTEGER)  # stem or caudex (outset) in mm
    stem_max_diameter = Column(INTEGER)  # stem or caudex (max) in mm
    height = Column(INTEGER)  # in mm
    pot_width_above = Column(INTEGER)  # in mm
    # pot_width_below = Column(INTEGER)  # in mm
    pot_circular = Column(BOOLEAN)  # false = quadratic
    pot_height = Column(INTEGER)  # in mm
    pot_material = Column(CHAR(50))
    soil = Column(CHAR(200))
    notes = Column(TEXT)


class Botany(Base):
    """botanical information"""
    __tablename__ = 'botany'

    species = Column(CHAR(100), primary_key=True, nullable=False)
    description = Column(CHAR(100))
    subgenus = Column(CHAR(100))
    genus = Column(CHAR(100))
    subfamilia = Column(CHAR(100))
    familia = Column(CHAR(100))
    ordo = Column(CHAR(100))
    subclassis = Column(CHAR(100))
    classis = Column(CHAR(100))
    divisio = Column(CHAR(100))
    superdivisio = Column(CHAR(100))
    subregnum = Column(CHAR(100))
    notes = Column(TEXT)
