from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import INTEGER, TEXT, VARCHAR, Column, DateTime, ForeignKey, Identity
from sqlalchemy.orm import Mapped, relationship

from plants import settings
from plants.extensions.orm import Base

if TYPE_CHECKING:
    from pathlib import Path

    from plants.modules.event.models import Event
    from plants.modules.plant.models import Plant
    from plants.modules.taxon.models import Taxon

logger = logging.getLogger(__name__)


class ImageKeyword(Base):
    """Keywords tagged at images."""

    __tablename__ = "image_keywords"
    image_id: int = Column(INTEGER, ForeignKey("image.id"), primary_key=True, nullable=False)
    # noinspection PyTypeChecker
    image: Mapped[Image] = relationship("Image", back_populates="keywords", foreign_keys=[image_id])
    keyword: str = Column(VARCHAR(60), primary_key=True, nullable=False)


class ImageToPlantAssociation(Base):
    """Plants tagged at images."""

    __tablename__ = "image_to_plant_association"
    __mapper_args__: ClassVar = {"confirm_deleted_rows": False}

    image_id: int = Column(INTEGER, ForeignKey("image.id"), primary_key=True, nullable=False)
    plant_id: int = Column(INTEGER, ForeignKey("plants.id"), primary_key=True, nullable=False)

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
    description: str | None = Column(VARCHAR(500))
    record_date_time: datetime = Column(DateTime(timezone=True), nullable=False)

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Image {self.id} {self.filename}>"

    @property
    def absolute_path(self) -> Path:
        return settings.paths.path_original_photos_uploaded.joinpath(self.filename)

    keywords: Mapped[list[ImageKeyword]] = relationship(
        "ImageKeyword",
        back_populates="image",
        uselist=True,
        cascade="all, delete-orphan",
    )

    plants: Mapped[list[Plant]] = relationship(
        "Plant", back_populates="images", secondary="image_to_plant_association", uselist=True
    )

    events: Mapped[list[Event]] = relationship(
        "Event",
        secondary="image_to_event_association",
        back_populates="images",
    )

    taxa: Mapped[list[Taxon]] = relationship(
        "Taxon",
        viewonly=True,  # only image_to_taxon_associations may be modified
        back_populates="images",
        secondary="image_to_taxon_association",
        uselist=True,
    )

    image_to_taxon_associations: Mapped[list[ImageToTaxonAssociation]] = relationship(
        "ImageToTaxonAssociation",
        viewonly=True,
        uselist=True,
        cascade="all, delete-orphan",
    )


class ImageToEventAssociation(Base):
    __tablename__ = "image_to_event_association"
    __mapper_args__: ClassVar = {"confirm_deleted_rows": False}
    image_id: int = Column(INTEGER, ForeignKey("image.id"), primary_key=True)
    event_id: int = Column(INTEGER, ForeignKey("event.id"), primary_key=True)

    def __repr__(self) -> str:
        return f"<ImageToEventAssociation {self.image_id} {self.event_id}>"


class ImageToTaxonAssociation(Base):
    __tablename__ = "image_to_taxon_association"
    __mapper_args__: ClassVar = {"confirm_deleted_rows": False}
    image_id: int = Column(INTEGER, ForeignKey("image.id"), primary_key=True)
    taxon_id: int = Column(INTEGER, ForeignKey("taxon.id"), primary_key=True)

    description: str | None = Column(TEXT)
