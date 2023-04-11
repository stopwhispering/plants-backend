from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy
from sqlalchemy import (
    INTEGER,
    TEXT,
    VARCHAR,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
)
from sqlalchemy.orm import Mapped, relationship

from plants.extensions.orm import Base
from plants.modules.event.enums import FBShapeSide, FBShapeTop, PotMaterial

if TYPE_CHECKING:
    from decimal import Decimal

    from plants.modules.image.models import Image
    from plants.modules.plant.models import Plant

logger = logging.getLogger(__name__)


class Soil(Base):
    __tablename__ = "soil"
    id: int = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    soil_name: str = Column(VARCHAR(100), unique=True, nullable=False)
    description: str | None = Column(TEXT)
    mix: str = Column(TEXT, nullable=False)

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # 1:n relationship to events (no need for bidirectional relationship)
    events: Mapped[list[Event]] = relationship("Event", back_populates="soil", uselist=True)


class Pot(Base):
    __tablename__ = "pot"
    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    event_id = Column(INTEGER, ForeignKey("event.id"), nullable=False)
    # event_id = Column(INTEGER)
    # 1:1 relationship to event
    event: Mapped[Event | None] = relationship("Event", back_populates="pot", uselist=False)

    material: PotMaterial = Column(sqlalchemy.Enum(PotMaterial), nullable=False)
    shape_top: FBShapeTop = Column(sqlalchemy.Enum(FBShapeTop), nullable=False)
    shape_side: FBShapeSide = Column(sqlalchemy.Enum(FBShapeSide), nullable=False)
    # 5 digits, 1 decimal --> max 9999.9
    diameter_width: Decimal | None = Column(Numeric(5, 1))  # type: ignore[valid-type]
    # pot_notes = Column(TEXT)

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # # 1:n relationship to events
    # events: Mapped[list[Event]] = relationship(
    #     "Event", back_populates="pot", uselist=True
    # )

    def __repr__(self):
        return (
            f"Pot(id={self.id}, material={self.material}, "
            f"shape_top={self.shape_top}, "
            f"shape_side={self.shape_side}, diameter_width={self.diameter_width})"
        )


class Observation(Base):
    """formerly: Measurement"""

    __tablename__ = "observation"
    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )

    event_id = Column(INTEGER, ForeignKey("event.id"), nullable=False)
    diseases: str | None = Column(TEXT)
    # 5 digits, 1 decimal --> max 9999.9  # stem or caudex (max)
    stem_max_diameter: Decimal | None = Column(Numeric(5, 1))  # type: ignore[valid-type]
    height: Decimal | None = Column(Numeric(5, 1))  # type: ignore[valid-type]
    observation_notes: str | None = Column(TEXT)

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # 1:1 relationship to event
    event: Mapped[Event | None] = relationship(
        "Event",
        back_populates="observation",
        uselist=False,
        foreign_keys=[event_id],
    )


class Event(Base):
    """Events."""

    __tablename__ = "event"
    id: int = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    date: str = Column(VARCHAR(10), nullable=False)  # yyyy-mm-dd
    event_notes = Column(TEXT)

    observation: Mapped[Observation | None] = relationship(
        "Observation",
        back_populates="event",
        # includes delete; we delete via SQLAlchemy, not via FK Constraint in db
        cascade="all, delete-orphan",
    )
    pot: Mapped[Pot | None] = relationship(
        "Pot",
        back_populates="event",
        # includes delete; we delete via SQLAlchemy, not via FK Constraint in db
        cascade="all, delete-orphan",
    )

    # n:1 relationship to soil, bi-directional
    soil_id = Column(INTEGER, ForeignKey("soil.id"))
    soil: Mapped[Soil | None] = relationship(
        "Soil", back_populates="events", foreign_keys=[soil_id]
    )

    plant_id = Column(INTEGER, ForeignKey("plants.id"), nullable=False)
    plant: Mapped[Plant] = relationship("Plant", back_populates="events")

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # 1:n relationship to the image/event link table
    images: Mapped[list[Image]] = relationship(
        "Image",
        secondary="image_to_event_association",
        back_populates="events",
    )
