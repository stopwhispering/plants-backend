from flask_2_ui5_py import throw_exception
from sqlalchemy import Column, INTEGER, CHAR, ForeignKey, BOOLEAN, TEXT
from sqlalchemy.orm import relationship

from plants_tagger.extensions.orm import Base, get_sql_session
from plants_tagger.util.OrmUtilMixin import OrmUtil


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
    taxon_to_trait_associations = relationship("TaxonToTraitAssociation", back_populates="taxon")

    # 1:n relationship to the image/taxon link table
    images = relationship(
            "Image",
            secondary='image_to_taxon_association'
            )
    image_to_taxon_associations = relationship("ImageToTaxonAssociation", back_populates="taxon")

    # # taxon to taxon property values: 1:n
    # property_values_taxon = relationship("PropertyValueTaxon", back_populates="taxon")

    @staticmethod
    def get_taxon_by_taxon_id(taxon_id: int, raise_exception: bool = False) -> object:
        taxon = get_sql_session().query(Taxon).filter(Taxon.id == taxon_id).first()
        if not taxon and raise_exception:
            throw_exception(f'Taxon not found in database: {taxon_id}')
        return taxon
