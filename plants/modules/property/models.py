from __future__ import annotations
import logging
from datetime import datetime
from sqlalchemy import Column, INTEGER, VARCHAR, ForeignKey, Identity, DateTime
from sqlalchemy.orm import relationship

from plants.extensions.orm import Base

logger = logging.getLogger(__name__)


class PropertyCategory(Base):
    """property categories"""
    __tablename__ = 'property_category'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    category_name = Column(VARCHAR(80), unique=True, nullable=False)
    # sort = Column(INTEGER)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    property_names = relationship("PropertyName", back_populates="property_category")


class PropertyName(Base):
    """new named properties - property names"""
    __tablename__ = 'property_name'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    property_name = Column(VARCHAR(240), nullable=False)  # eg."Epidermis texture"

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # NamedPropertyName to Category: n:1
    category_id = Column(INTEGER, ForeignKey('property_category.id'), nullable=False)
    property_category = relationship("PropertyCategory", back_populates="property_names")

    property_values = relationship("PropertyValue")


class PropertyValue(Base):
    """new named properties - property values for plants and taxa"""
    __tablename__ = 'property_value'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)

    property_name_id = Column(INTEGER, ForeignKey('property_name.id'), nullable=False)
    property_name = relationship("PropertyName", back_populates="property_values")

    property_value = Column(VARCHAR(240))  # e.g. "tuberculate/asperulous"

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # plant_id = Column(INTEGER, ForeignKey('plants.id'), nullable=False)
    plant_id = Column(INTEGER, ForeignKey('plants.id'))
    plant = relationship("Plant", back_populates="property_values_plant")

    taxon_id = Column(INTEGER, ForeignKey('taxon.id'))
    taxon = relationship("Taxon", back_populates="property_values_taxon")
