from __future__ import annotations
from flask_2_ui5_py import throw_exception
from sqlalchemy import Column, INTEGER, CHAR, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship

from plants_tagger.extensions.orm import Base, get_sql_session
from plants_tagger.util.OrmUtilMixin import OrmUtil


class Tag(Base, OrmUtil):
    """tags displayed in master view and created/deleted in details view"""
    __tablename__ = 'tags'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    text = Column(CHAR(20))
    icon = Column(CHAR(30))  # full uri, e.g. 'sap-icon://hint'
    state = Column(CHAR(11))  # Error, Information, None, Success, Warning
    last_update = Column(TIMESTAMP)
    # tag to plant: n:1
    plant_id = Column(INTEGER, ForeignKey('plants.id'))
    plant = relationship("Plant", back_populates="tags")

    # static query methods
    @staticmethod
    def get_tag_by_tag_id(tag_id: int, raise_exception: bool = False) -> Tag:
        tag = get_sql_session().query(Tag).filter(Tag.id == tag_id).first()
        if not tag and raise_exception:
            throw_exception(f'Tag not found in database: {tag_id}')
        return tag
