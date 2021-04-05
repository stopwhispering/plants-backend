from __future__ import annotations
import logging
from typing import List
from sqlalchemy import Column, INTEGER, CHAR, ForeignKey
from sqlalchemy.orm import relationship, Session

from plants.util.ui_utils import throw_exception
from plants.config import PROPERTY_CATEGORIES
from plants.util.OrmUtilMixin import OrmUtil
from plants.extensions.db import Base

logger = logging.getLogger(__name__)


class PropertyCategory(Base, OrmUtil):
    """property categories"""
    __tablename__ = 'property_category'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    category_name = Column(CHAR(80), unique=True, nullable=False)
    sort = Column(INTEGER)

    property_names = relationship("PropertyName", back_populates="property_category")

    # static query methods
    @staticmethod
    def get_cat_by_name(category_name: str, db: Session, raise_exception: bool = False) -> PropertyCategory:
        cat = db.query(PropertyCategory).filter(PropertyCategory.category_name == category_name).first()
        if not cat and raise_exception:
            throw_exception(f'Property Category not found in database: {category_name}')
        return cat

    @staticmethod
    def get_cat_by_id(category_id: int, db: Session, raise_exception: bool = False) -> PropertyCategory:
        cat = db.query(PropertyCategory).filter(PropertyCategory.id == category_id).first()
        if not cat and raise_exception:
            throw_exception(f'Property Category not found in database: {category_id}')
        return cat


class PropertyName(Base, OrmUtil):
    """new named properties - property names"""
    __tablename__ = 'property_name'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    property_name = Column(CHAR(240), nullable=False)  # eg."Epidermis texture"

    # NamedPropertyName to Category: n:1
    category_id = Column(INTEGER, ForeignKey('property_category.id'), nullable=False)
    property_category = relationship("PropertyCategory", back_populates="property_names")

    property_values = relationship("PropertyValue")


class PropertyValue(Base, OrmUtil):
    """new named properties - property values for plants and taxa"""
    __tablename__ = 'property_value'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)

    property_name_id = Column(INTEGER, ForeignKey('property_name.id'), nullable=False)
    property_name = relationship("PropertyName", back_populates="property_values")

    property_value = Column(CHAR(240))  # e.g. "tuberculate/asperulous"

    # plant_id = Column(INTEGER, ForeignKey('plants.id'), nullable=False)
    plant_id = Column(INTEGER, ForeignKey('plants.id'))
    plant = relationship("Plant", back_populates="property_values_plant")

    taxon_id = Column(INTEGER, ForeignKey('taxon.id'))
    taxon = relationship("Taxon", back_populates="property_values_taxon")

    # static query methods
    @staticmethod
    def get_by_id(property_value_id: int, db: Session, raise_exception: bool = False) -> PropertyValue:
        property_obj = db.query(PropertyValue).filter(PropertyValue.id ==
                                                      property_value_id).first()
        if not property_obj and raise_exception:
            throw_exception(f'No property values found for Property value ID: {property_value_id}')
        return property_obj

    @staticmethod
    def get_by_plant_id(plant_id: int, db: Session, raise_exception: bool = False) -> List[PropertyValue]:
        property_obj = db.query(PropertyValue).filter(PropertyValue.plant_id == int(plant_id),
                                                      PropertyValue.taxon_id.is_(None)).all()
        if not property_obj and raise_exception:
            throw_exception(f'No property values found for Plant ID: {plant_id}')
        return property_obj

    @staticmethod
    def get_by_taxon_id(taxon_id: int, db: Session, raise_exception: bool = False) -> List[PropertyValue]:
        property_obj = db.query(PropertyValue).filter(PropertyValue.taxon_id ==
                                                      taxon_id,
                                                      PropertyValue.taxon_id.is_(None)).all()
        if not property_obj and raise_exception:
            throw_exception(f'No property values found for Taxon ID: {taxon_id}')
        return property_obj

    def as_dict(self):
        """add some additional fields to mixin's as_dict, especially from relationships"""
        as_dict = super(PropertyValue, self).as_dict()
        as_dict['property_value_id'] = self.id
        del as_dict['id']

        # read segments from their respective linked tables
        as_dict['property_name'] = self.property_name.property_name
        as_dict['property_name_id'] = self.property_name.id
        as_dict['category_name'] = self.property_name.property_category.category_name
        as_dict['category_id'] = self.property_name.property_category.id
        as_dict['sort'] = self.property_name.property_category.sort

        return as_dict


def insert_property_categories(db: Session):
    # add Trait Categories if not existing upon initializing
    for t in PROPERTY_CATEGORIES:
        property_category = db.query(PropertyCategory).filter(PropertyCategory.category_name == t).first()
        if not property_category:
            logger.info(f'Inserting missing trait category into db: {t}')
            property_category = PropertyCategory(category_name=t)
            db.add(property_category)
    db.commit()