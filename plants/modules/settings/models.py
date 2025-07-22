from __future__ import annotations

from sqlalchemy import VARCHAR, Column
from sqlalchemy.types import DateTime

from plants.extensions.orm import Base

import datetime


class Settings(Base):
    """Simple Settings Table."""

    __tablename__ = "settings"
    key: str = Column(
        VARCHAR(50),  # e.g. "last_image_warning_after_n_days"
        primary_key=True,
        nullable=False,
    )
    value: str = Column(
        VARCHAR(30),  # e.g. "30" for the above key
        nullable=True,
    )

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)  # noqa