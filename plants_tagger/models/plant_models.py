from __future__ import annotations
from flask_2_ui5_py import throw_exception
from sqlalchemy import Column, CHAR, INTEGER, BOOLEAN, ForeignKey, TEXT, TIMESTAMP
from sqlalchemy.dialects.sqlite import DATE
from sqlalchemy.orm import relationship
import logging
import datetime
import json

from plants_tagger.services.PhotoDirectory import lock_photo_directory, get_photo_directory, NULL_DATE
from plants_tagger.models.taxon_models import Taxon
from plants_tagger.services.image_services import generate_previewimage_get_rel_path
from plants_tagger.services.os_paths import SUBDIRECTORY_PHOTOS_SEARCH
from plants_tagger.util.OrmUtilMixin import OrmUtil
from plants_tagger.extensions.orm import Base, get_sql_session
from plants_tagger.util.exif_utils import decode_record_date_time

logger = logging.getLogger(__name__)


class Plant(Base, OrmUtil):
    """my plants"""
    __tablename__ = 'plants'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    plant_name = Column(CHAR(100), unique=True, nullable=False)

    field_number = Column(CHAR(20))
    geographic_origin = Column(CHAR(100))
    nursery_source = Column(CHAR(100))
    propagation_type = Column(CHAR(30))

    count = Column(INTEGER)
    active = Column(BOOLEAN)
    generation_date = Column(DATE)
    generation_type = Column(CHAR(60))
    generation_notes = Column(CHAR(120))

    parent_plant_id = Column(INTEGER, ForeignKey('plants.id'))
    parent_plant = relationship("Plant",
                                primaryjoin='Plant.parent_plant_id==Plant.id',
                                remote_side=[id],
                                back_populates="descendant_plants")
    descendant_plants = relationship("Plant",
                                     primaryjoin="Plant.parent_plant_id==Plant.id",
                                     back_populates="parent_plant")

    parent_plant_pollen_id = Column(INTEGER, ForeignKey('plants.id'))
    parent_plant_pollen = relationship("Plant",
                                       primaryjoin='Plant.parent_plant_pollen_id==Plant.id',
                                       remote_side=[id],
                                       back_populates="descendant_plants_pollen")
    descendant_plants_pollen = relationship("Plant",
                                            primaryjoin="Plant.parent_plant_pollen_id==Plant.id",
                                            back_populates="parent_plant_pollen")
    # parent_plant_pollen_name = relationship("Plant", remote_side="Plant.id")

    # generation_origin = Column(CHAR(60))
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
    property_values_plant = relationship("PropertyValue", back_populates="plant")

    def as_dict(self):
        """add some additional fields to mixin's as_dict, especially from relationships"""
        as_dict = super(Plant, self).as_dict()
        as_dict['parent_plant'] = self.parent_plant.plant_name if self.parent_plant else None
        as_dict['parent_plant_pollen'] = self.parent_plant_pollen.plant_name if self.parent_plant_pollen else None
        as_dict['descendant_plants'] = [{
                'plant_name': p.plant_name,
                'id': p.id
                  } for p in (self.descendant_plants + self.descendant_plants_pollen)]

        # add botanical name and author
        if self.taxon:
            as_dict['botanical_name'] = self.taxon.name
            as_dict['taxon_authors'] = self.taxon.authors

        # overwrite None with empty string as workaround for some UI5 frontend bug with comboboxes
        if self.propagation_type is None:
            as_dict['propagation_type'] = ''

        # add path to preview image
        if self.filename_previewimage:  # supply relative path of original image
            rel_path_gen = generate_previewimage_get_rel_path(self.filename_previewimage)
            # there is a huge problem with the slashes
            as_dict['url_preview'] = json.dumps(rel_path_gen)[1:-1]
        else:
            as_dict['url_preview'] = None

        # add tags
        if self.tags:
            as_dict['tags'] = [t.as_dict() for t in self.tags]

        # add current soil
        if soil_events := [e for e in self.events if e.soil]:
            soil_events.sort(key=lambda e: e.date, reverse=True)
            as_dict['current_soil'] = {'soil_name': soil_events[0].soil.soil_name,
                                       'date':      soil_events[0].date}
        else:
            as_dict['current_soil'] = None

        # get latest photo record date per plant
        with lock_photo_directory:
            photo_directory = get_photo_directory()

            if latest_image := photo_directory.get_latest_date_per_plant(self.plant_name):
                as_dict['latest_image'] = {'path':       latest_image.path,
                                           'path_thumb': latest_image.path_thumb,
                                           'date':       latest_image.date}
            else:
                as_dict['latest_image_record_date'] = NULL_DATE
                as_dict['latest_image'] = None

        return as_dict

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

    def set_parent_plant(self, parent_plant_name: str = None):
        if parent_plant_name:
            self.parent_plant_id = self.get_plant_id_by_plant_name(parent_plant_name)
        else:
            self.parent_plant_id = None

    def set_parent_plant_pollen(self, parent_plant_pollen_name: str = None):
        if parent_plant_pollen_name:
            self.parent_plant_pollen_id = self.get_plant_id_by_plant_name(parent_plant_pollen_name)
        else:
            self.parent_plant_pollen_id = None

    # def set_generation_origin(self, generation_origin=None, plant: dict = None):
    #     self.generation_origin = plant.get('generation_origin') if plant else generation_origin

    def set_plant_notes(self, plant_notes=None, plant: dict = None):
        self.plant_notes = plant.get('plant_notes') if plant else plant_notes

    def set_filename_previewimage(self, filename_previewimage=None, plant: dict = None):
        filename_tmp = plant.get('filename_previewimage') if plant else filename_previewimage
        if not filename_tmp:
            self.filename_previewimage = None
            return

        # we need to remove the localService prefix
        if (filename_tmp := filename_tmp.replace('\\\\', '\\')).startswith(SUBDIRECTORY_PHOTOS_SEARCH):
            self.filename_previewimage = filename_tmp[len(SUBDIRECTORY_PHOTOS_SEARCH):]
        else:
            self.filename_previewimage = filename_tmp

    def set_taxon(self, taxon_id: int = None, plant: dict = None):
        taxon_id = plant.get('taxon_id') if plant else taxon_id
        if taxon_id:
            self.taxon = Taxon.get_taxon_by_taxon_id(taxon_id)
        else:
            self.taxon = None

    def set_last_update(self, last_update=None):
        self.last_update = last_update if last_update else datetime.datetime.now()

    # static query methods
    @staticmethod
    def get_plant_by_plant_name(plant_name: str, raise_exception: bool = False) -> Plant:
        plant = get_sql_session().query(Plant).filter(Plant.plant_name == plant_name).first()
        if not plant and raise_exception:
            throw_exception(f'Plant not found in database: {plant_name}')
        return plant

    @staticmethod
    def get_plant_by_plant_id(plant_id: int, raise_exception: bool = False) -> Plant:
        plant = get_sql_session().query(Plant).filter(Plant.id == plant_id).first()
        if not plant and raise_exception:
            throw_exception(f'Plant ID not found in database: {plant_id}')
        return plant

    @staticmethod
    def get_plant_id_by_plant_name(plant_name: str, raise_exception: bool = False) -> int:
        plant_id = get_sql_session().query(Plant.id).filter(Plant.plant_name == plant_name).scalar()
        if not plant_id and raise_exception:
            throw_exception(f'Plant ID not found in database: {plant_name}')
        return plant_id

    @staticmethod
    def get_plant_name_by_plant_id(plant_id: int, raise_exception: bool = False) -> str:
        plant_name = get_sql_session().query(Plant.plant_name).filter(Plant.id == plant_id).scalar()
        if not plant_name and raise_exception:
            throw_exception(f'Plant not found in database: {plant_id}')
        return plant_name
