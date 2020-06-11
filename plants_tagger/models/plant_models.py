from flask_2_ui5_py import throw_exception
from sqlalchemy import Column, CHAR, INTEGER, BOOLEAN, ForeignKey, TEXT, TIMESTAMP, Enum
from sqlalchemy.dialects.sqlite import DATE
from sqlalchemy.orm import relationship
import logging
import datetime

from plants_tagger.models.taxon_models import Taxon
from plants_tagger.services.os_paths import SUBDIRECTORY_PHOTOS_SEARCH

logger = logging.getLogger(__name__)

from plants_tagger.extensions.orm import Base, get_sql_session
from plants_tagger.util.exif import decode_record_date_time


class Plant(Base):
    """my plants"""
    __tablename__ = 'plants'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    plant_name = Column(CHAR(60), unique=True, nullable=False)

    field_number = Column(CHAR(20))
    geographic_origin = Column(CHAR(100))
    nursery_source = Column(CHAR(100))
    propagation_type = Column(Enum("vegetative", "generative", "unknown", name="propagation_type_enum"))

    count = Column(INTEGER)
    active = Column(BOOLEAN)  # plant may be inactive (e.g. separated) but not flagged dead; inactive ~ untraceable
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

    # setters
    def set_count(self, count=None, plant: dict = None):
        self.count = plant.get('count') if plant else count
        
    def set_field_number(self, field_number=None, plant: dict = None):
        self.field_number = plant.get('field_number') if plant else field_number
    
    def set_geographic_origin(self, geographic_origin=None, plant: dict = None):
        self.geographic_origin = plant.get('geographic_origin') if plant else geographic_origin

    def set_nursery_source(self, nursery_source=None, plant: dict = None):
        self.nursery_source = plant.get('nursery_source') if plant else nursery_source
        
    def set_propagation_type(self, propagation_type=None, plant: dict = None):
        self.propagation_type = plant.get('propagation_type') if plant else propagation_type
        
    def set_active(self, active=None, plant: dict = None):
        self.active = plant.get('active') if plant else active
        
    def set_generation_date(self, generation_date=None, plant: dict = None):
        generation_date_tmp = plant.get('generation_date') if plant else generation_date
        if generation_date_tmp:
            self.generation_date = decode_record_date_time(generation_date_tmp) if generation_date_tmp else None
        
    def set_generation_type(self, generation_type=None, plant: dict = None):
        self.generation_type = plant.get('generation_type') if plant else generation_type
        
    def set_generation_notes(self, generation_notes=None, plant: dict = None):
        self.generation_notes = plant.get('generation_notes') if plant else generation_notes

    def set_mother_plant(self, mother_plant_name: str = None):
        if mother_plant_name:
            self.mother_plant_id = self.get_plant_id_by_plant_name(mother_plant_name)
        else:
            self.mother_plant_id = None
        
    def set_generation_origin(self, generation_origin=None, plant: dict = None):
        self.generation_origin = plant.get('generation_origin') if plant else generation_origin
        
    def set_plant_notes(self, plant_notes=None, plant: dict = None):
        self.plant_notes = plant.get('plant_notes') if plant else plant_notes
        
    def set_filename_previewimage(self, filename_previewimage=None, plant: dict = None):
        filename_tmp = plant.get('filename_previewimage') if plant else filename_previewimage
        if not filename_tmp:
            self.filename_previewimage = None
            return

        # we need to remove the localService prefix
        filename_tmp = filename_tmp.replace('\\\\', '\\')
        if filename_tmp.startswith(SUBDIRECTORY_PHOTOS_SEARCH):
            self.filename_previewimage = filename_tmp[len(SUBDIRECTORY_PHOTOS_SEARCH):]
        else:
            self.filename_previewimage = filename_tmp

    def set_taxon(self, taxon_id=None, plant:dict = None):
        taxon_id = plant.get('taxon_id') if plant else taxon_id
        if taxon_id:
            self.taxon = Taxon.get_taxon_by_taxon_id(taxon_id)
        else:
            self.taxon = None

    def set_last_update(self, last_update=None ):
        self.last_update = last_update if last_update else datetime.datetime.now()

    # static query methods
    @staticmethod
    def get_plant_by_plant_name(plant_name: str, raise_exception: bool = False) -> object:
        plant = get_sql_session().query(Plant).filter(Plant.plant_name == plant_name).first()
        if not plant and raise_exception:
            throw_exception(f'Plant not found in database: {plant_name}')
        return plant

    @staticmethod
    def get_plant_id_by_plant_name(plant_name: str, raise_exception: bool = False) -> int:
        plant_id = get_sql_session().query(Plant.id).filter(Plant.plant_name == plant_name).scalar()
        if not plant_id and raise_exception:
            throw_exception(f'Plant ID not found in database: {plant_name}')
        return plant_id


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
