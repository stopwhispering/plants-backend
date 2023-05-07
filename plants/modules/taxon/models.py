from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import (
    BOOLEAN,
    INTEGER,
    TEXT,
    VARCHAR,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
)
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.types import DateTime

from plants.extensions.orm import Base
from plants.modules.image.models import Image
from plants.modules.taxon.enums import Establishment, FBRank

if TYPE_CHECKING:
    from plants.modules.plant.models import Plant


class Distribution(Base):
    """Geographic distribution."""

    __tablename__ = "distribution"

    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    name: str = Column(VARCHAR(40), nullable=False)
    establishment: Establishment = Column(sa.Enum(Establishment), nullable=False)
    feature_id: str = Column(VARCHAR(5), nullable=False)
    tdwg_code: str = Column(VARCHAR(10), nullable=False)
    tdwg_level: int = Column(INTEGER, nullable=False)

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    taxon_id: int = Column(INTEGER, ForeignKey("taxon.id"), nullable=False)
    taxon: Mapped[Taxon] = relationship("Taxon", back_populates="distribution")


class Taxon(Base):
    """botanical details non-technical key is name (unique constraint) lsid is unique, too, amont
    those taxa with is_custom == False (no constraint, asserted programmatically)"""

    __tablename__ = "taxon"

    id: int = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    name: str = Column(VARCHAR(100), nullable=False)
    full_html_name: str = Column(VARCHAR(120), nullable=False)
    species: str | None = Column(VARCHAR(100))
    genus: str = Column(VARCHAR(100), nullable=False)
    family: str = Column(VARCHAR(100), nullable=False)

    infraspecies: str | None = Column(VARCHAR(40))
    custom_infraspecies: str | None = Column(VARCHAR(40))
    custom_rank: FBRank | None = Column(sa.Enum(FBRank))
    cultivar: str | None = Column(VARCHAR(30))
    affinis: str | None = Column(VARCHAR(40))

    is_custom: bool = Column(BOOLEAN, nullable=False)
    custom_suffix: str | None = Column(VARCHAR(30))

    rank: str = Column(VARCHAR(30), nullable=False)
    taxonomic_status: str = Column(VARCHAR(100), nullable=False)
    name_published_in_year: int = Column(INTEGER, nullable=False)
    synonym: bool = Column(BOOLEAN, nullable=False)
    lsid: str = Column(VARCHAR(50), nullable=False)
    authors: str = Column(VARCHAR(100), nullable=False)
    basionym: str | None = Column(VARCHAR(100))
    synonyms_concat: str | None = Column(VARCHAR(500))
    distribution_concat: str | None = Column(VARCHAR(200))
    hybrid: bool = Column(BOOLEAN, nullable=False)
    hybridgenus: bool = Column(BOOLEAN, nullable=False)
    gbif_id: int | None = Column(INTEGER)  # Global Biodiversity Information Facility
    custom_notes: str | None = Column(TEXT)  # may be updated on web frontend

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    plants: Mapped[list[Plant]] = relationship("Plant", back_populates="taxon", uselist=True)
    distribution: Mapped[list[Distribution]] = relationship(
        "Distribution", back_populates="taxon", uselist=True
    )

    # 1:n relationship to the photo_file/taxon link table
    images: Mapped[list[Image]] = relationship(
        "Image",
        back_populates="taxa",
        secondary="image_to_taxon_association",
        uselist=True,
    )

    # taxon to occurence images (n:m)
    occurrence_images: Mapped[list[TaxonOccurrenceImage]] = relationship(
        "TaxonOccurrenceImage",
        back_populates="taxa",
        secondary="taxon_to_occurrence_association",
        uselist=True,
    )

    def __repr__(self) -> str:
        return f"<Taxon - {self.id} - {self.name}>"


class TaxonOccurrenceImage(Base):
    """Botanical details."""

    __tablename__ = "taxon_ocurrence_image"

    occurrence_id: int = Column(BIGINT, primary_key=True, nullable=False)
    img_no: int = Column(INTEGER, primary_key=True, nullable=False)
    gbif_id: int = Column(INTEGER, primary_key=True, nullable=False)
    scientific_name: str = Column(VARCHAR(100), nullable=False)
    basis_of_record: str = Column(VARCHAR(25), nullable=False)
    verbatim_locality: str | None = Column(VARCHAR(120))
    photographed_at: datetime = Column(DateTime(timezone=True), nullable=False)
    # date: datetime = Column(DateTime(timezone=True), nullable=False)
    creator_identifier: str = Column(VARCHAR(100), nullable=False)
    publisher_dataset: str | None = Column(VARCHAR(100))
    references: str | None = Column(VARCHAR(120))
    href: str = Column(VARCHAR(150), nullable=False)
    filename_thumbnail: str = Column(VARCHAR(120), nullable=False)

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # relationship to Taxon (m:n) via TaxonToOccurrenceImageAssociation
    taxa: Mapped[list[Taxon]] = relationship(
        "Taxon",
        secondary="taxon_to_occurrence_association",
        back_populates="occurrence_images",
        uselist=True,
    )

    def __repr__(self) -> str:
        return f"<TaxonOccurrenceImage - {self.occurrence_id} - {self.img_no} " f"{self.gbif_id}>"


class TaxonToOccurrenceAssociation(Base):
    """Link table for taxon to occurrence images."""

    __tablename__ = "taxon_to_occurrence_association"

    taxon_id = Column(INTEGER, ForeignKey("taxon.id"), primary_key=True, nullable=False)
    occurrence_id = Column(BIGINT, primary_key=True, nullable=False)
    img_no = Column(INTEGER, primary_key=True, nullable=False)
    gbif_id = Column(INTEGER, primary_key=True, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # noinspection PyTypeChecker
    __table_args__ = (  # type: ignore[var-annotated]
        ForeignKeyConstraint(
            (occurrence_id, img_no, gbif_id),
            (
                TaxonOccurrenceImage.occurrence_id,
                TaxonOccurrenceImage.img_no,
                TaxonOccurrenceImage.gbif_id,
            ),
        ),
        {},
    )
