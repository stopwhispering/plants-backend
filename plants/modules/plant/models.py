from __future__ import annotations

import datetime
import logging
from operator import attrgetter
from typing import TYPE_CHECKING

from sqlalchemy import BOOLEAN, INTEGER, TEXT, VARCHAR, Column, ForeignKey, Identity
from sqlalchemy.orm import Mapped, foreign, relationship, remote  # noqa
from sqlalchemy.types import DateTime

from plants.extensions.orm import Base

if TYPE_CHECKING:
    from plants.modules.event.models import Event
    from plants.modules.image.models import Image, ImageToPlantAssociation
    from plants.modules.pollination.models import Florescence
    from plants.modules.taxon.models import Taxon

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

    field_number: str = Column(VARCHAR(20))
    geographic_origin: str = Column(VARCHAR(100))
    nursery_source: str = Column(VARCHAR(100))
    propagation_type: str = Column(VARCHAR(30))  # todo enum

    deleted: bool = Column(BOOLEAN, nullable=False)

    active: bool = Column(BOOLEAN, nullable=False)
    # todo enum,  only set if active == False
    cancellation_reason: str = Column(VARCHAR(60))
    cancellation_date = Column(
        DateTime(timezone=True)
    )  # todo rename to datetime or make it date type

    generation_notes: str = Column(VARCHAR(250))

    images: Mapped[list[Image]] = relationship(
        "Image",
        secondary="image_to_plant_association",
        overlaps="plants,image_to_plant_associations",  # silence warnings
        uselist=True,
    )
    image_to_plant_associations: Mapped[list[ImageToPlantAssociation]] = relationship(
        "ImageToPlantAssociation",
        back_populates="plant",
        overlaps="plants",  # silence warnings
        uselist=True,
    )

    parent_plant_id = Column(INTEGER, ForeignKey("plants.id"))
    parent_plant: Mapped[Plant] = relationship(
        "Plant",
        primaryjoin="Plant.parent_plant_id==Plant.id",
        remote_side=[id],  # noqa
        back_populates="descendant_plants",
    )
    descendant_plants: Mapped[list[Plant]] = relationship(
        "Plant",
        primaryjoin="Plant.parent_plant_id==Plant.id",
        back_populates="parent_plant",
    )

    parent_plant_pollen_id = Column(INTEGER, ForeignKey("plants.id"))
    parent_plant_pollen: Mapped[Plant] = relationship(
        "Plant",
        primaryjoin="Plant.parent_plant_pollen_id==Plant.id",
        remote_side=[id],  # noqa
        back_populates="descendant_plants_pollen",
    )
    descendant_plants_pollen: Mapped[list[Plant]] = relationship(
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
    taxon: Mapped[Taxon] = relationship("Taxon", back_populates="plants")

    # plant to tag: 1:n
    tags: Mapped[list[Tag]] = relationship("Tag", back_populates="plant")

    # plant to event: 1:n
    events: Mapped[list[Event]] = relationship("Event", back_populates="plant")

    # plant to florescences: 1:n
    florescences: Mapped[list[Florescence]] = relationship(
        "Florescence", back_populates="plant"
    )

    count_stored_pollen_containers = Column(INTEGER)

    def __repr__(self):
        return f"<Plant [{self.id}] {self.plant_name}>"

    @property
    def descendant_plants_all(self) -> list[Plant]:
        return self.descendant_plants + self.descendant_plants_pollen

    sibling_plants: Mapped[list[Plant]] = relationship(
        "Plant",
        primaryjoin="(foreign(Plant.parent_plant_id) == "
        "remote(Plant.parent_plant_id)) & "
        "("
        "   ("
        "       (foreign(Plant.parent_plant_pollen_id.is_(None))) & "
        "       (remote(Plant.parent_plant_pollen_id.is_(None)))"
        "   ) | ("
        "       (foreign(Plant.parent_plant_pollen_id) == "
        "remote(Plant.parent_plant_pollen_id)) "
        "   )"
        ") & "
        "(foreign(Plant.id) != remote(Plant.id)) ",
        foreign_keys="Plant.parent_plant_id",
        viewonly=True,
        uselist=True,
    )

    same_taxon_plants: Mapped[list[Plant]] = relationship(
        "Plant",
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
        return None

    @property
    def current_soil(self) -> dict | None:
        soil_events = [e for e in self.events if e.soil is not None]
        if soil_events:
            soil_events.sort(key=lambda e: e.date, reverse=True)
            return {
                "soil_name": soil_events[0].soil.soil_name,  # type:ignore
                "date": soil_events[0].date,
            }
        return None

    @property
    def botanical_name(self) -> str | None:
        return self.taxon.name if self.taxon else None

    @property
    def full_botanical_html_name(self) -> str | None:
        return self.taxon.full_html_name if self.taxon else None

    @property
    def taxon_authors(self) -> str | None:
        return self.taxon.authors if self.taxon and self.taxon.authors else None


class Tag(Base):
    """Tags displayed in master view and created/deleted in details view."""

    __tablename__ = "tags"
    id: int = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    text: str | None = Column(VARCHAR(20))
    # icon = Column(VARCHAR(30))  # full uri, e.g. 'sap-icon://hint'
    # Error, Information, None, Success, Warning
    state: str | None = Column(VARCHAR(12))
    # tag to plant: n:1
    plant_id: int | None = Column(INTEGER, ForeignKey("plants.id"))
    plant: Mapped[Plant | None] = relationship("Plant", back_populates="tags")

    last_update = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow
    )
