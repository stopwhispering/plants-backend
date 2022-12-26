from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, INTEGER, VARCHAR, ForeignKey, Identity, DateTime
from sqlalchemy.orm import relationship, Session

from plants.util.ui_utils import throw_exception
from plants.util.OrmUtilMixin import OrmUtil
from plants.extensions.db import Base


class Tag(Base, OrmUtil):
    """tags displayed in master view and created/deleted in details view"""
    __tablename__ = 'tags'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    text = Column(VARCHAR(20))
    # icon = Column(VARCHAR(30))  # full uri, e.g. 'sap-icon://hint'
    state = Column(VARCHAR(12))  # Error, Information, None, Success, Warning
    # tag to plant: n:1
    plant_id = Column(INTEGER, ForeignKey('plants.id'))
    plant = relationship("Plant", back_populates="tags")

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # static query methods
    @staticmethod
    def get_tag_by_tag_id(tag_id: int, db: Session, raise_exception: bool = False) -> Tag:
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag and raise_exception:
            throw_exception(f'Tag not found in database: {tag_id}')
        return tag
