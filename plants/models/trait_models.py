# from __future__ import annotations
# from sqlalchemy import Column, INTEGER, ForeignKey, CHAR, Identity
# from sqlalchemy.orm import relationship, Session
#
# from plants.util.ui_utils import throw_exception
# from plants.util.OrmUtilMixin import OrmUtil
# from plants.extensions.db import Base


# class TaxonToTraitAssociation(Base):
#     __tablename__ = 'taxon_to_trait_association'
#     taxon_id = Column(INTEGER, ForeignKey('taxon.id'), primary_key=True)
#     trait_id = Column(INTEGER, ForeignKey('trait.id'), primary_key=True)
#     status = Column(VARCHAR(20))
#
#     taxon = relationship('Taxon',
#                          back_populates='taxon_to_trait_associations',
#                          overlaps="traits"  # silence warnings
#                          )
#     trait = relationship('Trait',
#                          back_populates='taxon_to_trait_associations',
#                          overlaps="traits"  # silence warnings
#                          )


# class Trait(Base, OrmUtil):
#     """traits"""
#     __tablename__ = 'trait'
#     id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
#     trait = Column(VARCHAR(240))
#
#     # 1:n relationship to the taxon/traits link table
#     taxa = relationship(
#             "Taxon",
#             secondary='taxon_to_trait_association',
#             overlaps="taxon,taxon_to_trait_associations,traits,trait"  # silence warnings
#             )
#     taxon_to_trait_associations = relationship("TaxonToTraitAssociation",
#                                                back_populates="trait",
#                                                overlaps="taxa,traits"  # silence warnings
#                                                )
#
#     # trait to trait category: n:1
#     trait_category_id = Column(INTEGER, ForeignKey('trait_category.id'))
#     trait_category = relationship("TraitCategory", back_populates="traits")


# class TraitCategory(Base, OrmUtil):
#     """trait categories"""
#     __tablename__ = 'trait_category'
#     id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
#     category_name = Column(VARCHAR(80))
#     sort_flag = Column(INTEGER)
#
#     traits = relationship("Trait",
#                           back_populates="trait_category")
#
#     # static query methods
#     @staticmethod
#     def get_cat_by_name(category_name: str, db: Session, raise_exception: bool = False) -> TraitCategory:
#         cat = db.query(TraitCategory).filter(TraitCategory.category_name == category_name).first()
#         if not cat and raise_exception:
#             throw_exception(f'Trait Category not found in database: {category_name}')
#         return cat
