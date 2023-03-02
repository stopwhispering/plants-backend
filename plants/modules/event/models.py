from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from decimal import Decimal

    from plants.modules.event.enums import FBShapeSide
    from plants.modules.image.models import Image, ImageToEventAssociation
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
    soil_name: str = Column(VARCHAR(100), nullable=False)  # todo make unique
    description: str | None = Column(TEXT)
    mix: str = Column(TEXT, nullable=False)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # 1:n relationship to events (no need for bidirectional relationship)
    events: Mapped[list[Event]] = relationship(
        "Event", back_populates="soil", uselist=True
    )


class Pot(Base):
    __tablename__ = "pot"
    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    material = Column(VARCHAR(50))  # todo enum
    shape_top: str | None = Column(VARCHAR(20))  # todo enum   # oval, square, circle
    # todo enum  # flat, very flat, high, very high
    shape_side: FBShapeSide | None = Column(VARCHAR(20))
    # 5 digits, 1 decimal --> max 9999.9
    diameter_width: Decimal | None = Column(Numeric(5, 1))  # type: ignore[valid-type]
    # pot_notes = Column(TEXT)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # 1:n relationship to events
    events: Mapped[list[Event]] = relationship(
        "Event", back_populates="pot", uselist=True
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
    # plant_name = Column(VARCHAR(60), nullable=False)
    diseases: str | None = Column(TEXT)
    # 5 digits, 1 decimal --> max 9999.9  # stem or caudex (max)
    stem_max_diameter: Decimal | None = Column(  # type: ignore[valid-type]
        Numeric(5, 1)
    )
    height: Decimal | None = Column(Numeric(5, 1))  # type: ignore[valid-type]
    # location = Column(VARCHAR(30))
    observation_notes: str | None = Column(TEXT)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # 1:1 relationship to event
    event: Mapped[Event | None] = relationship(
        "Event", back_populates="observation", uselist=False
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
    date: str = Column(VARCHAR(12), nullable=False)  # yyyy-mm-dd  # todo make it 10
    event_notes = Column(TEXT)

    # 1:1 relationship to observation (joins usually from event to observation, not the
    # other way around)
    observation_id = Column(INTEGER, ForeignKey("observation.id"))
    observation: Mapped[Observation | None] = relationship(
        "Observation", back_populates="event"
    )

    # n:1 relationship to pot, bi-directional
    pot_id = Column(INTEGER, ForeignKey("pot.id"))
    pot: Mapped[Pot | None] = relationship("Pot", back_populates="events")

    # n:1 relationship to soil, bi-directional
    soil_id = Column(INTEGER, ForeignKey("soil.id"))
    soil: Mapped[Soil | None] = relationship("Soil", back_populates="events")

    # event to plant: n:1, bi-directional
    plant_id = Column(INTEGER, ForeignKey("plants.id"), nullable=False)
    plant: Mapped[Plant] = relationship("Plant", back_populates="events")

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # 1:n relationship to the photo_file/event link table
    images: Mapped[list[Image]] = relationship(
        "Image",
        secondary="image_to_event_association",
        overlaps="events,image,image_to_event_associations,event",  # silence warnings
    )
    image_to_event_associations: Mapped[list[ImageToEventAssociation]] = relationship(
        "ImageToEventAssociation", back_populates="event", overlaps="events,images"
    )  # silence warnings
