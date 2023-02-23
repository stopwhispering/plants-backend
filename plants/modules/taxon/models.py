from __future__ import annotations

from datetime import datetime

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
from sqlalchemy.orm import relationship
from sqlalchemy.types import DateTime

from plants.extensions.orm import Base


class Distribution(Base):
    """Geographic distribution."""

    __tablename__ = "distribution"

    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    name = Column(VARCHAR(40))
    establishment = Column(VARCHAR(15))
    feature_id = Column(VARCHAR(5))
    tdwg_code = Column(VARCHAR(10))
    tdwg_level = Column(INTEGER)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    taxon_id = Column(INTEGER, ForeignKey("taxon.id"))
    taxon = relationship("Taxon", back_populates="distribution")


class Taxon(Base):
    """botanical details non-technical key is name (unique constraint) lsid is unique,
    too, amont those taxa with is_custom == False (no constraint, asserted
    programmatically)"""

    __tablename__ = "taxon"

    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    name = Column(VARCHAR(100), nullable=False)
    full_html_name = Column(VARCHAR(120), nullable=False)  # todo populate
    species = Column(VARCHAR(100))
    genus = Column(VARCHAR(100))
    family = Column(VARCHAR(100))
    # phylum = Column(VARCHAR(100))

    infraspecies = Column(VARCHAR(40))
    custom_infraspecies = Column(VARCHAR(40))
    custom_rank = Column(VARCHAR(30))
    cultivar = Column(VARCHAR(30))
    affinis = Column(VARCHAR(40))

    is_custom = Column(BOOLEAN, nullable=False)
    custom_suffix = Column(VARCHAR(30))

    rank = Column(VARCHAR(30), nullable=False)
    taxonomic_status = Column(VARCHAR(100))
    name_published_in_year = Column(INTEGER)
    synonym = Column(BOOLEAN)
    lsid = Column(VARCHAR(50), nullable=False)
    authors = Column(VARCHAR(100))
    basionym = Column(VARCHAR(100))
    synonyms_concat = Column(VARCHAR(500))
    distribution_concat = Column(VARCHAR(200))
    hybrid = Column(BOOLEAN, nullable=False)
    hybridgenus = Column(BOOLEAN)
    gbif_id = Column(INTEGER)  # Global Biodiversity Information Facility
    custom_notes = Column(TEXT)  # may be updated on web frontend

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    plants = relationship("Plant", back_populates="taxon")
    distribution = relationship("Distribution", back_populates="taxon")

    # 1:n relationship to the photo_file/taxon link table
    images = relationship("Image", secondary="image_to_taxon_association")
    image_to_taxon_associations = relationship(
        "ImageToTaxonAssociation",
        back_populates="taxon",
        overlaps="images",  # silence warnings
    )

    # taxon to occurence images (n:m)
    occurrence_images = relationship(
        "TaxonOccurrenceImage",
        back_populates="taxa",
        secondary="taxon_to_occurrence_association",
    )

    def __repr__(self):
        return f"<Taxon - {self.id} - {self.name}>"


class TaxonOccurrenceImage(Base):
    """Botanical details."""

    __tablename__ = "taxon_ocurrence_image"

    occurrence_id = Column(BIGINT, primary_key=True, nullable=False)
    img_no = Column(INTEGER, primary_key=True, nullable=False)
    # gbif_id = Column(INTEGER, ForeignKey('taxon.gbif_id'), primary_key=True, nullable=False)
    gbif_id = Column(INTEGER, primary_key=True, nullable=False)
    scientific_name = Column(VARCHAR(100))
    basis_of_record = Column(VARCHAR(25))
    verbatim_locality = Column(VARCHAR(120))
    date = Column(DateTime(timezone=True))  # todo rename datetime or make it date type
    creator_identifier = Column(VARCHAR(100))
    publisher_dataset = Column(VARCHAR(100))
    references = Column(VARCHAR(120))
    href = Column(VARCHAR(150))
    filename_thumbnail = Column(VARCHAR(120))  # todo switch to other id

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # relationship to Taxon (m:n) via TaxonToOccurrenceImageAssociation
    taxa = relationship(
        "Taxon",
        secondary="taxon_to_occurrence_association",
        back_populates="occurrence_images",
    )

    def __repr__(self):
        return f"<TaxonOccurrenceImage - {self.occurrence_id} - {self.img_no} {self.gbif_id}>"


class TaxonToOccurrenceAssociation(Base):
    """Link table for taxon to occurrence images."""

    __tablename__ = "taxon_to_occurrence_association"

    taxon_id = Column(INTEGER, ForeignKey("taxon.id"), primary_key=True, nullable=False)
    occurrence_id = Column(BIGINT, primary_key=True, nullable=False)
    img_no = Column(INTEGER, primary_key=True, nullable=False)
    gbif_id = Column(INTEGER, primary_key=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
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
