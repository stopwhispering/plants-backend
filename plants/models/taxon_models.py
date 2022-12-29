from __future__ import annotations

from datetime import datetime

from sqlalchemy import (Column, INTEGER, VARCHAR, ForeignKey,
                        BOOLEAN, TEXT, Identity, ForeignKeyConstraint,
                        )
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.types import DateTime
from sqlalchemy.orm import relationship, Session

from plants.util.ui_utils import throw_exception
from plants.util.OrmUtilMixin import OrmUtil
from plants.extensions.db import Base


class Distribution(Base):
    """geographic distribution"""
    __tablename__ = 'distribution'

    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    name = Column(VARCHAR(40))
    establishment = Column(VARCHAR(15))
    feature_id = Column(VARCHAR(5))
    tdwg_code = Column(VARCHAR(10))
    tdwg_level = Column(INTEGER)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    taxon_id = Column(INTEGER, ForeignKey('taxon.id'))
    taxon = relationship("Taxon", back_populates="distribution")


class Taxon(Base, OrmUtil):
    """
    botanical details
    non-technical key is name (unique constraint)
    lsid is unique, too, amont those taxa with is_custom == False (no constraint, asserted programmatically)
    """
    __tablename__ = 'taxon'

    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    name = Column(VARCHAR(100), nullable=False)
    is_custom = Column(BOOLEAN, nullable=False)
    subsp = Column(VARCHAR(100))
    species = Column(VARCHAR(100))
    subgen = Column(VARCHAR(100))
    genus = Column(VARCHAR(100))
    family = Column(VARCHAR(100))
    phylum = Column(VARCHAR(100))
    kingdom = Column(VARCHAR(100))
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
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    plants = relationship("Plant", back_populates="taxon")
    distribution: list = relationship("Distribution", back_populates="taxon")

    # # 1:n relationship to the taxon/traits link table
    # traits = relationship(
    #     "Trait",
    #     secondary='taxon_to_trait_association'
    # )
    # taxon_to_trait_associations = relationship("TaxonToTraitAssociation",
    #                                            back_populates="taxon",
    #                                            overlaps="traits",  # silence warnings
    #                                            )

    # 1:n relationship to the photo_file/taxon link table
    images = relationship(
        "Image",
        secondary='image_to_taxon_association'
    )
    image_to_taxon_associations = relationship("ImageToTaxonAssociation",
                                               back_populates="taxon",
                                               overlaps="images"  # silence warnings
                                               )

    # taxon to occurence images (n:m)
    occurrence_images: list = relationship("TaxonOccurrenceImage",
                                           back_populates="taxa",
                                           secondary='taxon_to_occurrence_association'
                                           )

    # occurrence_images = relationship('TaxonOccurrenceImage',
    #                                  secondary='taxon_to_occurrence_association',
    #                                  # foreign_keys='[taxon.id]',
    #                                  # primaryjoin='Taxon.id == TaxonToOccurrenceAssociation.taxon_id',
    #                                  # primaryjoin="and_(User.id==Address.user_id, " "Address.city=='Boston')"
    #                                  primaryjoin="and_(Taxon.id == TaxonToOccurrenceAssociation.taxon_id, TaxonToOccurrenceAssociation.occurrence_id==TaxonOccurrenceImage.occurrence_id)",
    #                                  back_populates='taxa')

    # occurrence_images = relationship('TaxonOccurrenceImage',
    #                                  secondary='taxon_to_occurrence_association',
    #                                  primaryjoin='Taxon.id == foreign(TaxonToOccurrenceAssociation.taxon_id)',
    #                                  secondaryjoin='and_(TaxonOccurrenceImage.occurrence_id == TaxonToOccurrenceAssociation.occurrence_id, TaxonOccurrenceImage.img_no == foreign(TaxonToOccurrenceAssociation.img_no), TaxonOccurrenceImage.gbif_id == foreign(TaxonToOccurrenceAssociation.gbif_id))'
    #                                  )

    # taxon to taxon property values: 1:n
    property_values_taxon = relationship("PropertyValue", back_populates="taxon")

    @staticmethod
    def get_taxon_by_taxon_id(taxon_id: int, db: Session, raise_exception: bool = False) -> Taxon:
        taxon = db.query(Taxon).filter(Taxon.id == taxon_id).first()
        if not taxon and raise_exception:
            throw_exception(f'Taxon not found in database: {taxon_id}')
        return taxon

    def as_dict(self):
        """add some additional fields to mixin's as_dict, especially from relationships"""
        as_dict = super(Taxon, self).as_dict()
        if not as_dict['synonym']:  # overwrite None with False
            as_dict['synonym'] = False

        # as_dict['ipni_id_short'] = self.fq_id if self.fq_id else None

        return as_dict


class TaxonOccurrenceImage(Base, OrmUtil):
    """botanical details"""
    __tablename__ = 'taxon_ocurrence_image'

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
    filename_thumbnail = Column(VARCHAR(120))

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # relationship to taxa (m:n) via gbif_id
    # taxon = relationship("Taxon",
    #                      back_populates="occurrence_images",
    #                      # foreign_keys=[taxon_id]
    #                      )

    # relationship to Taxon (m:n) via TaxonToOccurrenceImageAssociation
    taxa = relationship("Taxon",
                        secondary='taxon_to_occurrence_association',
                        back_populates="occurrence_images",
                        )
    # taxon_to_occurrence_associations = relationship("TaxonToOccurrenceImageAssociation",
    #                                                 foreign_keys=[occurrence_id, img_no, gbif_id]
    #                                                 )


class TaxonToOccurrenceAssociation(Base, OrmUtil):
    """link table for taxon to occurrence images"""
    __tablename__ = 'taxon_to_occurrence_association'

    taxon_id = Column(INTEGER, ForeignKey('taxon.id'), primary_key=True, nullable=False)
    occurrence_id = Column(BIGINT, primary_key=True, nullable=False)
    img_no = Column(INTEGER, primary_key=True, nullable=False)
    gbif_id = Column(INTEGER, primary_key=True, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (ForeignKeyConstraint((occurrence_id, img_no, gbif_id),
                                           (TaxonOccurrenceImage.occurrence_id,
                                            TaxonOccurrenceImage.img_no,
                                            TaxonOccurrenceImage.gbif_id)),
                      {})
    # taxon = relationship("Taxon", back_populates="taxon_to_occurrence_associations")
    # occurrence = relationship("TaxonOccurrenceImage",
    #                           back_populates="taxon_to_occurrence_associations",
    #                           foreign_keys=[occurrence_id, img_no, gbif_id]
    #                           )
