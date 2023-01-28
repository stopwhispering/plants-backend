from __future__ import annotations

from operator import attrgetter
from typing import Optional
from sqlalchemy import Column, INTEGER, BOOLEAN, ForeignKey, TEXT, Identity, VARCHAR
from sqlalchemy.orm import relationship, Session
from sqlalchemy.orm import foreign, remote  # noqa
from sqlalchemy.types import DateTime
import logging
import datetime

from plants import settings
from plants.shared.message__services import throw_exception
from plants.modules.taxon.models import Taxon
from plants.shared.orm_utils import OrmAsDict
from plants.extensions.orm import Base
from plants.modules.plant.schemas import FPlant

logger = logging.getLogger(__name__)


class Plant(Base, OrmAsDict):
    """my plants"""
    __tablename__ = 'plants'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    plant_name = Column(VARCHAR(100), unique=True, nullable=False)

    field_number = Column(VARCHAR(20))
    geographic_origin = Column(VARCHAR(100))
    nursery_source = Column(VARCHAR(100))
    propagation_type = Column(VARCHAR(30))  # todo enum

    active = Column(BOOLEAN)
    deleted = Column(BOOLEAN)
    cancellation_reason = Column(VARCHAR(60))  # todo enum,  only set if active == False
    cancellation_date = Column(DateTime(timezone=True))  # todo rename to datetime or make it date type

    generation_notes = Column(VARCHAR(250))

    images = relationship(
            "Image",
            secondary='image_to_plant_association',
            overlaps="plants,image_to_plant_associations"  # silence warnings
            )
    image_to_plant_associations = relationship("ImageToPlantAssociation",
                                               back_populates="plant",
                                               overlaps="plants"  # silence warnings
                                               )

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

    # generation_origin = Column(VARCHAR(60))
    plant_notes = Column(TEXT)
    filename_previewimage = Column(VARCHAR(240))  # original filen. of the photo_file that is set as preview photo_file

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    last_update = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)

    # plant to taxon: n:1
    taxon_id = Column(INTEGER, ForeignKey('taxon.id'))
    taxon = relationship("Taxon", back_populates="plants")

    # plant to tag: 1:n
    tags = relationship("Tag", back_populates="plant")

    # plant to event: 1:n
    events = relationship("Event", back_populates="plant")

    # plant to plant property values: 1:n
    property_values_plant = relationship("PropertyValue", back_populates="plant")

    # plant to florescences: 1:n
    florescences = relationship("Florescence", back_populates="plant")

    count_stored_pollen_containers = Column(INTEGER)

    @property
    def descendant_plants_all(self) -> list[Plant]:
        return self.descendant_plants + self.descendant_plants_pollen

    sibling_plants = relationship(
            "Plant",
            primaryjoin="(foreign(Plant.parent_plant_id) == remote(Plant.parent_plant_id)) & "
                        "("
                        "   ("
                        "       (foreign(Plant.parent_plant_pollen_id.is_(None))) & "
                        "       (remote(Plant.parent_plant_pollen_id.is_(None)))"
                        "   ) | ("
                        "       (foreign(Plant.parent_plant_pollen_id) == remote(Plant.parent_plant_pollen_id)) "
                        "   )"
                        ") & "
                        "(foreign(Plant.id) != remote(Plant.id)) ",
            foreign_keys='Plant.parent_plant_id',
            viewonly=True,
            uselist=True
            )

    same_taxon_plants = relationship(
            "Plant",
            # primaryjoin="Plant.taxon_id == Plant.taxon_id",  # works
            # primaryjoin="foreign(Plant.taxon_id) == remote(Plant.taxon_id)",  # works
            # primaryjoin="and_(foreign(Plant.taxon_id) == remote(Plant.taxon_id), foreign(Plant.id) != remote("
            #             "Plant.id))",  # works
            primaryjoin="(~Plant.plant_name.contains('×')) & "
                        "(foreign(Plant.taxon_id) == remote(Plant.taxon_id)) & "
                        "(foreign(Plant.id) != remote(Plant.id))",
            foreign_keys='Plant.taxon_id',
            viewonly=True,
            uselist=True
            )

    @property
    def latest_image(self):
        if self.images:
            try:
                latest_image = max(self.images, key=attrgetter('record_date_time'))
            except TypeError:  # no image with a record date
                return None
            return latest_image

    @property
    def current_soil(self) -> dict:
        if soil_events := [e for e in self.events if e.soil]:
            soil_events.sort(key=lambda e: e.date, reverse=True)
            return {'soil_name': soil_events[0].soil.soil_name,
                    'date':      soil_events[0].date}

    @property
    def botanical_name(self) -> str:
        if self.taxon:
            return self.taxon.name

    @property
    def full_botanical_html_name(self) -> str:
        if self.taxon:
            return self.taxon.full_html_name

    @property
    def taxon_authors(self) -> str:
        if self.taxon:
            return self.taxon.authors

    def as_dict(self):
        """add some additional fields to mixin's as_dict, especially from relationships
        merge descendant_plants_pollen into descendant_plants"""
        raise NotImplementedError('use get_plant_as_dict() instead')

    def set_filename_previewimage(self, plant: Optional[FPlant] = None):
        """we actually set the path to preview photo_file (the original photo_file, not the thumbnail) excluding
        the photos-subdir part of the uri
        """
        if not plant.filename_previewimage:
            self.filename_previewimage = None
            return

        # generate_previewimage_if_not_exists(original_image_rel_path=plant.filename_previewimage)

        # rmeove photos-subdir from path if required (todo: still required somewhere?)
        if plant.filename_previewimage.is_relative_to(settings.paths.subdirectory_photos):
            self.filename_previewimage = plant.filename_previewimage.relative_to(
                settings.paths.subdirectory_photos).as_posix()
        else:
            self.filename_previewimage = plant.filename_previewimage.as_posix()

    def set_taxon(self, db: Session, taxon_id: Optional[int]):
        if taxon_id:
            self.taxon = Taxon.get_taxon_by_taxon_id(taxon_id, db)
        else:
            self.taxon = None

    # def set_last_update(self, last_update=None):
    #     self.last_update = last_update if last_update else datetime.datetime.now()

    # static query methods
    @staticmethod
    def get_plant_by_plant_name(plant_name: str, db: Session, raise_exception: bool = False) -> Plant | None:
        plant = db.query(Plant).filter(Plant.plant_name == plant_name).first()
        if not plant and raise_exception:
            throw_exception(f'Plant not found in database: {plant_name}')
        return plant

    @staticmethod
    def get_plant_by_plant_id(plant_id: int, db: Session, raise_exception: bool = False) -> Plant | None:
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


class Tag(Base, OrmAsDict):
    """tags displayed in master view and created/deleted in details view"""
    __tablename__ = 'tags'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    text = Column(VARCHAR(20))
    # icon = Column(VARCHAR(30))  # full uri, e.g. 'sap-icon://hint'
    state = Column(VARCHAR(12))  # Error, Information, None, Success, Warning
    # tag to plant: n:1
    plant_id = Column(INTEGER, ForeignKey('plants.id'))
    plant = relationship("Plant", back_populates="tags")

    last_update = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)

    # static query methods
    @staticmethod
    def get_tag_by_tag_id(tag_id: int, db: Session, raise_exception: bool = False) -> Tag | None:
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag and raise_exception:
            throw_exception(f'Tag not found in database: {tag_id}')
        return tag