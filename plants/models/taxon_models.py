from __future__ import annotations
from sqlalchemy import Column, INTEGER, CHAR, ForeignKey, BOOLEAN, TEXT
from sqlalchemy.dialects.sqlite import DATETIME
from sqlalchemy.orm import relationship, Session

from plants.util.ui_utils import throw_exception
from plants.util.OrmUtilMixin import OrmUtil
from plants.extensions.db import Base


class Distribution(Base):
    """geographic distribution"""
    __tablename__ = 'distribution'

    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    name = Column(CHAR(40))
    establishment = Column(CHAR(15))
    feature_id = Column(CHAR(5))
    tdwg_code = Column(CHAR(10))
    tdwg_level = Column(INTEGER)

    taxon_id = Column(INTEGER, ForeignKey('taxon.id'))
    taxon = relationship("Taxon", back_populates="distribution")


class Taxon(Base, OrmUtil):
    """botanical details"""
    __tablename__ = 'taxon'

    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    name = Column(CHAR(100))
    is_custom = Column(BOOLEAN)
    subsp = Column(CHAR(100))
    species = Column(CHAR(100))
    subgen = Column(CHAR(100))
    genus = Column(CHAR(100))
    family = Column(CHAR(100))
    phylum = Column(CHAR(100))
    kingdom = Column(CHAR(100))
    rank = Column(CHAR(30))
    taxonomic_status = Column(CHAR(100))
    name_published_in_year = Column(INTEGER)
    synonym = Column(BOOLEAN)
    fq_id = Column(CHAR(50))
    authors = Column(CHAR(100))
    basionym = Column(CHAR(100))
    synonyms_concat = Column(CHAR(200))
    distribution_concat = Column(CHAR(200))
    hybrid = Column(BOOLEAN)
    hybridgenus = Column(BOOLEAN)
    gbif_id = Column(INTEGER)  # Global Biodiversity Information Facility
    powo_id = Column(CHAR(50))
    custom_notes = Column(TEXT)  # may be updated on web frontend

    plants = relationship("Plant", back_populates="taxon")
    distribution = relationship("Distribution", back_populates="taxon")

    # 1:n relationship to the taxon/traits link table
    traits = relationship(
            "Trait",
            secondary='taxon_to_trait_association'
            )
    taxon_to_trait_associations = relationship("TaxonToTraitAssociation",
                                               back_populates="taxon",
                                               overlaps="traits",  # silence warnings
                                               )

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
    occurence_images = relationship("TaxonOccurrenceImage", back_populates="taxa")

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

        as_dict['ipni_id_short'] = self.fq_id if self.fq_id else None

        return as_dict


class TaxonOccurrenceImage(Base, OrmUtil):
    """botanical details"""
    __tablename__ = 'taxon_ocurrence_image'

    occurrence_id = Column(INTEGER, primary_key=True, nullable=False)
    img_no = Column(INTEGER, primary_key=True, nullable=False)
    gbif_id = Column(INTEGER, ForeignKey('taxon.gbif_id'), primary_key=True, nullable=False)
    scientific_name = Column(CHAR(100))
    basis_of_record = Column(CHAR(25))
    verbatim_locality = Column(CHAR(120))
    date = Column(DATETIME)
    creator_identifier = Column(CHAR(100))
    publisher_dataset = Column(CHAR(100))
    references = Column(CHAR(120))
    href = Column(CHAR(120))
    filename_thumbnail = Column(CHAR(120))

    # relationship to taxa (m:n) via gbif_id
    taxa = relationship("Taxon", back_populates="occurence_images")
