from sqlalchemy import Column, CHAR, INTEGER, TEXT
from sqlalchemy.dialects.sqlite import DATETIME

from plants_tagger.extensions.orm import Base


class History(Base):
    """history of certain events; used for error-finding et alia"""
    __tablename__ = 'history'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)

    timestamp = Column(DATETIME)
    plant_id = Column(INTEGER)
    plant_name = Column(CHAR(60))
    description = Column(TEXT)
