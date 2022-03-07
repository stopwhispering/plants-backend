from __future__ import annotations

from pathlib import PurePath
from typing import Optional, List
from sqlalchemy import Column, CHAR, INTEGER, BOOLEAN, ForeignKey, TEXT, TIMESTAMP, DATETIME
from sqlalchemy.orm import relationship, Session
import logging
import datetime
import json

from plants import config
from plants.models.event_models import Event
from plants.models.property_models import PropertyValue
from plants.models.tag_models import Tag
from plants.util.ui_utils import throw_exception
from plants.services.PhotoDirectory import lock_photo_directory, get_photo_directory, NULL_DATE
from plants.models.taxon_models import Taxon
from plants.services.image_services import generate_previewimage_get_rel_path
from plants.util.OrmUtilMixin import OrmUtil
from plants.extensions.db import Base
from plants.validation.plant_validation import PPlant

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

    active = Column(BOOLEAN)
    cancellation_reason = Column(CHAR(60))  # only set if active == False
    cancellation_date = Column(DATETIME)

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

    # generation_origin = Column(CHAR(60))
    plant_notes = Column(TEXT)
    filename_previewimage = Column(CHAR(240))  # original filename of the image that is set as preview image
    hide = Column(BOOLEAN)
    last_update = Column(TIMESTAMP, nullable=False)

    # plant to taxon: n:1
    taxon_id = Column(INTEGER, ForeignKey('taxon.id'))
    taxon = relationship("Taxon", back_populates="plants")

    # plant to tag: 1:n
    tags: List[Tag] = relationship("Tag", back_populates="plant")

    # plant to event: 1:n
    events: List[Event] = relationship("Event", back_populates="plant")

    # plant to plant property values: 1:n
    property_values_plant: List[PropertyValue] = relationship("PropertyValue", back_populates="plant")

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
            rel_path_gen = generate_previewimage_get_rel_path(PurePath(self.filename_previewimage))
            # there is a huge problem with the slashes
            as_dict['url_preview'] = json.dumps(rel_path_gen.as_posix())[1:-1]
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

    def set_parent_plant(self, db: Session, parent_plant_name: str = None):
        if parent_plant_name:
            self.parent_plant_id = self.get_plant_id_by_plant_name(parent_plant_name, db)
        else:
            self.parent_plant_id = None

    def set_parent_plant_pollen(self, db: Session, parent_plant_pollen_name: str = None):
        if parent_plant_pollen_name:
            self.parent_plant_pollen_id = self.get_plant_id_by_plant_name(parent_plant_pollen_name, db)
        else:
            self.parent_plant_pollen_id = None

    def set_filename_previewimage(self, plant: Optional[PPlant] = None):
        """we actually set the path to preview image (the original image, not the thumbnail) excluding
        the photos-subdir part of the uri
        """
        if not plant.filename_previewimage:
            self.filename_previewimage = None
            return

        # the photos-subdir may be part of the supplied path
        # but need not (depending on whether already saved)
        if plant.filename_previewimage.is_relative_to(config.subdirectory_photos):
            self.filename_previewimage = plant.filename_previewimage.relative_to(config.subdirectory_photos).as_posix()
        else:
            plant.filename_previewimage.as_posix()

    def set_taxon(self, db: Session, taxon_id: Optional[int]):
        if taxon_id:
            self.taxon = Taxon.get_taxon_by_taxon_id(taxon_id, db)
        else:
            self.taxon = None

    def set_last_update(self, last_update=None):
        self.last_update = last_update if last_update else datetime.datetime.now()

    # static query methods
    @staticmethod
    def get_plant_by_plant_name(plant_name: str, db: Session, raise_exception: bool = False) -> Plant:
        plant = db.query(Plant).filter(Plant.plant_name == plant_name).first()
        if not plant and raise_exception:
            throw_exception(f'Plant not found in database: {plant_name}')
        return plant

    @staticmethod
    def get_plant_by_plant_id(plant_id: int, db: Session, raise_exception: bool = False) -> Plant:
        plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant and raise_exception:
            throw_exception(f'Plant ID not found in database: {plant_id}')
        return plant

    @staticmethod
    def get_plant_id_by_plant_name(plant_name: str, db: Session, raise_exception: bool = False) -> int:
        plant_id = db.query(Plant.id).filter(Plant.plant_name == plant_name).scalar()
        if not plant_id and raise_exception:
            throw_exception(f'Plant ID not found in database: {plant_name}')
        return plant_id

    @staticmethod
    def get_plant_name_by_plant_id(plant_id: int, db: Session, raise_exception: bool = False) -> str:
        plant_name = db.query(Plant.plant_name).filter(Plant.id == plant_id).scalar()
        if not plant_name and raise_exception:
            throw_exception(f'Plant not found in database: {plant_id}')
        return plant_name
