from sqlalchemy import Column, INTEGER, ForeignKey, CHAR
from sqlalchemy.orm import relationship

from plants_tagger.extensions.orm import Base
from plants_tagger.util.OrmUtilMixin import OrmUtil


class TaxonToTraitAssociation(Base):
    __tablename__ = 'taxon_to_trait_association'
    taxon_id = Column(INTEGER, ForeignKey('taxon.id'), primary_key=True)
    trait_id = Column(INTEGER, ForeignKey('trait.id'), primary_key=True)
    status = Column(CHAR(20))

    taxon = relationship('Taxon', back_populates='taxon_to_trait_associations')
    trait = relationship('Trait', back_populates='taxon_to_trait_associations')


class Trait(Base, OrmUtil):
    """traits"""
    __tablename__ = 'trait'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    trait = Column(CHAR(240))

    # 1:n relationship to the taxon/traits link table
    taxa = relationship(
            "Taxon",
            secondary='taxon_to_trait_association'
            )
    taxon_to_trait_associations = relationship("TaxonToTraitAssociation", back_populates="trait")

    # trait to trait category: n:1
    trait_category_id = Column(INTEGER, ForeignKey('trait_category.id'))
    trait_category = relationship("TraitCategory", back_populates="traits")


class TraitCategory(Base):
    """trait categories"""
    __tablename__ = 'trait_category'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    category_name = Column(CHAR(80))
    sort_flag = Column(INTEGER)

    traits = relationship("Trait", back_populates="trait_category")
    # property_names = relationship("PropertyName", back_populates="property_category")
