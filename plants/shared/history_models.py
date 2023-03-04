from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import INTEGER, TEXT, VARCHAR, Column, Identity
from sqlalchemy.types import DateTime

from plants.extensions.orm import Base

if TYPE_CHECKING:
    import datetime


class History(Base):
    """History of certain events; used for error-finding et alia."""

    __tablename__ = "history"
    id: int = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    # todo rename
    timestamp: datetime.datetime = Column(DateTime(timezone=True), nullable=False)
    plant_id: int = Column(INTEGER, nullable=False)
    plant_name: str = Column(VARCHAR(100), nullable=False)
    description: str = Column(TEXT, nullable=False)
