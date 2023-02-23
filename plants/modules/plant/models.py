from __future__ import annotations

import datetime
import logging
from operator import attrgetter

from sqlalchemy import (BOOLEAN, INTEGER, TEXT, VARCHAR, Column, ForeignKey,
                        Identity)
from sqlalchemy.orm import foreign, relationship, remote  # noqa
from sqlalchemy.types import DateTime

from plants.extensions.orm import Base

logger = logging.getLogger(__name__)


class Plant(Base):
    """My plants."""

    __tablename__ = "plants"
    id: int = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    plant_name: str = Column(VARCHAR(100), unique=True, nullable=False)

    field_number = Column(VARCHAR(20))
    geographic_origin = Column(VARCHAR(100))
    nursery_source = Column(VARCHAR(100))
    propagation_type = Column(VARCHAR(30))  # todo enum

    deleted = Column(BOOLEAN, nullable=False)

    active = Column(BOOLEAN, nullable=False)
    cancellation_reason = Column(VARCHAR(60))  # todo enum,  only set if active == False
    cancellation_date = Column(
        DateTime(timezone=True)
    )  # todo rename to datetime or make it date type

    generation_notes = Column(VARCHAR(250))

    images = relationship(
        "Image",
        secondary="image_to_plant_association",
        overlaps="plants,image_to_plant_associations",  # silence warnings
    )
    image_to_plant_associations = relationship(
        "ImageToPlantAssociation",
        back_populates="plant",
        overlaps="plants",  # silence warnings
    )

    parent_plant_id = Column(INTEGER, ForeignKey("plants.id"))
    parent_plant = relationship(
        "Plant",
        primaryjoin="Plant.parent_plant_id==Plant.id",
        remote_side=[id],  # noqa
        back_populates="descendant_plants",
    )
    descendant_plants = relationship(
        "Plant",
        primaryjoin="Plant.parent_plant_id==Plant.id",
        back_populates="parent_plant",
    )

    parent_plant_pollen_id = Column(INTEGER, ForeignKey("plants.id"))
    parent_plant_pollen = relationship(
        "Plant",
        primaryjoin="Plant.parent_plant_pollen_id==Plant.id",
        remote_side=[id],  # noqa
        back_populates="descendant_plants_pollen",
    )
    descendant_plants_pollen = relationship(
        "Plant",
        primaryjoin="Plant.parent_plant_pollen_id==Plant.id",
        back_populates="parent_plant_pollen",
    )

    # generation_origin = Column(VARCHAR(60))
    plant_notes = Column(TEXT)
    filename_previewimage = Column(
        VARCHAR(240)
    )  # original filen. of the photo_file that is set as preview photo_file

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow
    )
    last_update = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)

    # plant to taxon: n:1
    taxon_id = Column(INTEGER, ForeignKey("taxon.id"))
    taxon = relationship("Taxon", back_populates="plants")

    # plant to tag: 1:n
    tags = relationship("Tag", back_populates="plant")

    # plant to event: 1:n
    events = relationship("Event", back_populates="plant")

    # plant to florescences: 1:n
    florescences = relationship("Florescence", back_populates="plant")

    count_stored_pollen_containers = Column(INTEGER)

    def __repr__(self):
        return f"<Plant [{self.id}] {self.plant_name}>"

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
        foreign_keys="Plant.parent_plant_id",
        viewonly=True,
        uselist=True,
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
        foreign_keys="Plant.taxon_id",
        viewonly=True,
        uselist=True,
    )

    @property
    def latest_image(self):
        if self.images:
            try:
                latest_image = max(self.images, key=attrgetter("record_date_time"))
            except TypeError:  # no image with a record date
                return None
            return latest_image

    @property
    def current_soil(self) -> dict:
        if soil_events := [e for e in self.events if e.soil]:
            soil_events.sort(key=lambda e: e.date, reverse=True)
            return {
                "soil_name": soil_events[0].soil.soil_name,
                "date": soil_events[0].date,
            }

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


class Tag(Base):
    """Tags displayed in master view and created/deleted in details view."""

    __tablename__ = "tags"
    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    text = Column(VARCHAR(20))
    # icon = Column(VARCHAR(30))  # full uri, e.g. 'sap-icon://hint'
    state = Column(VARCHAR(12))  # Error, Information, None, Success, Warning
    # tag to plant: n:1
    plant_id = Column(INTEGER, ForeignKey("plants.id"))
    plant = relationship("Plant", back_populates="tags")

    last_update = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow
    )
