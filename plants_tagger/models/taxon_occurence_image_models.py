from __future__ import annotations

from sqlalchemy import Column, INTEGER, CHAR
from sqlalchemy.dialects.sqlite import DATETIME

from plants_tagger.extensions.orm import Base
from plants_tagger.util.OrmUtilMixin import OrmUtil


class TaxonOccurrenceImage(Base, OrmUtil):
    """botanical details"""
    __tablename__ = 'taxon_ocurrence_image'

    occurrence_id = Column(INTEGER, primary_key=True, nullable=False)
    img_no = Column(INTEGER, primary_key=True, nullable=False)
    gbif_id = Column(INTEGER, primary_key=True, nullable=False)
    scientific_name = Column(CHAR(100))
    basis_of_record = Column(CHAR(25))
    verbatim_locality = Column(CHAR(120))
    date = Column(DATETIME)
    creator_identifier = Column(CHAR(100))
    publisher_dataset = Column(CHAR(100))
    references = Column(CHAR(120))
    href = Column(CHAR(120))
    filename_thumbnail = Column(CHAR(120))
