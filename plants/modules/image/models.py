from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

from sqlalchemy import (
    INTEGER,
    TEXT,
    TIMESTAMP,
    VARCHAR,
    Column,
    DateTime,
    ForeignKey,
    Identity,
)
from sqlalchemy.orm import Mapped, relationship

from plants import settings
from plants.extensions.orm import Base

if TYPE_CHECKING:
    from plants.modules.event.models import Event
    from plants.modules.plant.models import Plant
    from plants.modules.taxon.models import Taxon

logger = logging.getLogger(__name__)


class ImageKeyword(Base):
    """Keywords tagged at images."""

    __tablename__ = "image_keywords"
    image_id: int = Column(
        INTEGER, ForeignKey("image.id"), primary_key=True, nullable=False
    )
    # todo max 30 for new keywords
    keyword: str = Column(VARCHAR(100), primary_key=True, nullable=False)
    image: Mapped[Image] = relationship("Image", back_populates="keywords")


class ImageToPlantAssociation(Base):
    """Plants tagged at images."""

    __tablename__ = "image_to_plant_association"
    image_id: int = Column(
        INTEGER, ForeignKey("image.id"), primary_key=True, nullable=False
    )
    plant_id: int = Column(
        INTEGER, ForeignKey("plants.id"), primary_key=True, nullable=False
    )

    # silence warnings for deletions of associated entities
    # (image has image_to_plant_association and plants)
    __mapper_args__ = {
        "confirm_deleted_rows": False,
    }

    image: Mapped[Image] = relationship(
        "Image",
        back_populates="image_to_plant_associations",
        overlaps="images,plants",  # silence warnings
    )

    plant: Mapped[Plant] = relationship(
        "Plant",
        back_populates="image_to_plant_associations",
        overlaps="images,plants",  # silence warnings
    )

    def __repr__(self) -> str:
        return f"<ImageToPlantAssociation {self.image_id} {self.plant_id}>"


class Image(Base):
    """Image paths."""

    # images themselves are stored in file system
    # this table is only used to link events to images
    __tablename__ = "image"
    id: int = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    filename: str = Column(VARCHAR(150), unique=True, nullable=False)  # pseudo-key
    # relative path to the original image file incl. file name
    relative_path: str = Column(VARCHAR(240), nullable=False)
    description: str | None = Column(VARCHAR(500))
    record_date_time: datetime = Column(TIMESTAMP, nullable=False)

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Image {self.id} {self.filename}>"

    @property
    def absolute_path(self) -> Path:
        return settings.paths.path_photos.parent.joinpath(
            PurePath(self.relative_path)
        )  # todo what?

    keywords: Mapped[list[ImageKeyword]] = relationship(
        "ImageKeyword", back_populates="image", uselist=True
    )

    plants: Mapped[list[Plant]] = relationship(
        "Plant", secondary="image_to_plant_association", uselist=True
    )
    image_to_plant_associations: Mapped[list[ImageToPlantAssociation]] = relationship(
        "ImageToPlantAssociation",
        back_populates="image",
        overlaps="plants",  # silence warnings
        uselist=True,
    )

    # 1:n relationship to the image/event link table
    events: Mapped[list[Event]] = relationship(
        "Event", secondary="image_to_event_association"
    )
    image_to_event_associations: Mapped[list[ImageToEventAssociation]] = relationship(
        "ImageToEventAssociation",
        back_populates="image",
        overlaps="events",  # silence warnings
        uselist=True,
    )

    # 1:n relationship to the image/taxon link table
    taxa: Mapped[list[Taxon]] = relationship(
        "Taxon",
        secondary="image_to_taxon_association",
        overlaps="image_to_taxon_associations,images",  # silence warnings
        uselist=True,
    )
    image_to_taxon_associations: Mapped[list[ImageToTaxonAssociation]] = relationship(
        "ImageToTaxonAssociation",
        back_populates="image",
        overlaps="images,taxa",  # silence warnings
        uselist=True,
    )


class ImageToEventAssociation(Base):
    __tablename__ = "image_to_event_association"
    image_id: int = Column(INTEGER, ForeignKey("image.id"), primary_key=True)
    event_id: int = Column(INTEGER, ForeignKey("event.id"), primary_key=True)

    # silence warnings for deletions of associated entities (image has
    # image_to_event_association and events)
    __mapper_args__ = {
        "confirm_deleted_rows": False,
    }

    image: Mapped[Image] = relationship(
        "Image",
        back_populates="image_to_event_associations",
        overlaps="events",  # silence warnings
    )
    event: Mapped[Event] = relationship(
        "Event",
        back_populates="image_to_event_associations",
        overlaps="events",  # silence warnings
    )


class ImageToTaxonAssociation(Base):
    __tablename__ = "image_to_taxon_association"
    image_id: int = Column(INTEGER, ForeignKey("image.id"), primary_key=True)
    taxon_id: int = Column(INTEGER, ForeignKey("taxon.id"), primary_key=True)

    description: str | None = Column(TEXT)

    # silence warnings for deletions of associated entities (image has
    # image_to_taxa_association and taxa)
    __mapper_args__ = {
        "confirm_deleted_rows": False,
    }

    image: Mapped[Image] = relationship(
        "Image",
        back_populates="image_to_taxon_associations",
        overlaps="images,taxa",  # silence warnings
    )
    taxon: Mapped[Taxon] = relationship(
        "Taxon",
        back_populates="image_to_taxon_associations",
        overlaps="images,taxa",  # silence warnings
    )
