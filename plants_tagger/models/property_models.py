from sqlalchemy import Column, INTEGER, CHAR, ForeignKey, BOOLEAN
from sqlalchemy.orm import relationship

from plants_tagger.extensions.orm import Base


class PropertyName(Base):
    """new named properties - property names"""
    __tablename__ = 'property_name'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    property_name = Column(CHAR(240), nullable=False)  # eg."Epidermis texture"

    # NamedPropertyName to Category: n:1
    category_id = Column(INTEGER, ForeignKey('trait_category.id'), nullable=False)
    property_category = relationship("TraitCategory", back_populates="property_names")


class PropertyValueTaxon(Base):
    """new named properties - property values for taxa"""
    __tablename__ = 'property_value_taxon'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)

    property_name_id = Column(INTEGER, ForeignKey('property_name.id'), nullable=False)
    property_name = relationship("PropertyName")
    property_value = Column(CHAR(240))  # e.g. "tuberculate/asperulous"

    # family = Column(CHAR(100))
    # genus = Column(CHAR(100))
    # subgen = Column(CHAR(100))
    # species = Column(CHAR(100))
    # subsp = Column(CHAR(100))
    taxon_id = Column(INTEGER, ForeignKey('taxon.id'))  # formerly only used for custom names
    taxon = relationship("Taxon", back_populates="property_values_taxon")

    rank = Column(CHAR(30))  # e.g. "subspecies", "subspecies", or "variety"  # todo useful?
    override_higher_ranks = Column(BOOLEAN)  # true to only show this value; false to addTo higher r.val  # todo useful?


class PropertyValuePlant(Base):
    """new named properties - property values for plants"""
    __tablename__ = 'property_value_plant'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)

    property_name_id = Column(INTEGER, ForeignKey('property_name.id'), nullable=False)
    property_name = relationship("PropertyName")
    property_value = Column(CHAR(240))  # e.g. "tuberculate/asperulous"

    plant_name = Column(CHAR(60), ForeignKey('plants.plant_name'), nullable=False)
    plant = relationship("Plant", back_populates="property_values_plant")