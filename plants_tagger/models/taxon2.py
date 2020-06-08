from sqlalchemy import Column, INTEGER, CHAR, ForeignKey, BOOLEAN, TEXT
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import exists

from plants_tagger.extensions.orm import Base, get_sql_session


class Taxon2(Base):
    """botanical details"""
    __tablename__ = 'taxon2'

    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    parent_id = Column(INTEGER, ForeignKey('taxon2.id'))
    name = Column(CHAR(100))
    is_custom = Column(BOOLEAN)
    rank = Column(CHAR(30))

    taxonomic_status = Column(CHAR(100))
    name_published_in_year = Column(INTEGER)
    scientific_name = Column(CHAR(160))
    synonym = Column(BOOLEAN)
    authors = Column(CHAR(100))
    basionym = Column(CHAR(100))
    synonyms_concat = Column(CHAR(200))
    distribution_concat = Column(CHAR(200))
    hybrid = Column(BOOLEAN)
    hybridgenus = Column(BOOLEAN)
    lsid = Column(CHAR(50))  # IPNI Life Sciences Identifier, = fqId for Powo and IPNI
    gbif_nub = Column(INTEGER)  # Global Biodiversity Information Facility
    custom_notes = Column(TEXT)  # may be updated on web frontend

    @hybrid_property
    def lsid_short(self):
        """note: property is not included in __dict__"""
        return self.lsid[24:] if self.lsid and len(self.lsid) > 24 else ''

    # children = relationship("Taxon2")
    children = relationship("Taxon2", backref=backref('parent', remote_side=[id]))

    def exists(self, lsid: str = None):
        return get_sql_session().query(exists().where(self.lsid == lsid)).scalar()
