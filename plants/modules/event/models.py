from __future__ import annotations

import logging
from datetime import datetime

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
from sqlalchemy.orm import relationship

from plants.extensions.orm import Base

logger = logging.getLogger(__name__)


class Soil(Base):
    __tablename__ = "soil"
    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    soil_name = Column(VARCHAR(100), nullable=False)  # todo make unique
    description = Column(TEXT)
    mix = Column(TEXT)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # 1:n relationship to events (no need for bidirectional relationship)
    events = relationship("Event", back_populates="soil")


class Pot(Base):
    __tablename__ = "pot"
    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    material = Column(VARCHAR(50))  # todo enum
    shape_top = Column(VARCHAR(20))  # todo enum   # oval, square, circle
    shape_side = Column(VARCHAR(20))  # todo enum  # flat, very flat, high, very high
    diameter_width = Column(Numeric(5, 1))  # 5 digits, 1 decimal --> max 9999.9
    # pot_notes = Column(TEXT)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # 1:n relationship to events
    events = relationship("Event", back_populates="pot")


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
    diseases = Column(TEXT)
    stem_max_diameter = Column(
        Numeric(5, 1)
    )  # 5 digits, 1 decimal --> max 9999.9  # stem or caudex (max)
    height = Column(Numeric(5, 1))  # 5 digits, 1 decimal --> max 9999.9
    # location = Column(VARCHAR(30))
    observation_notes = Column(TEXT)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # 1:1 relationship to event
    event = relationship("Event", back_populates="observation", uselist=False)


class Event(Base):
    """Events."""

    __tablename__ = "event"
    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    date = Column(VARCHAR(12), nullable=False)  # yyyy-mm-dd  # todo make it 10
    event_notes = Column(TEXT)

    # 1:1 relationship to observation (joins usually from event to observation, not the other way around)
    observation_id = Column(INTEGER, ForeignKey("observation.id"))
    observation = relationship("Observation", back_populates="event")

    # n:1 relationship to pot, bi-directional
    pot_id = Column(INTEGER, ForeignKey("pot.id"))
    pot = relationship("Pot", back_populates="events")

    # n:1 relationship to soil, bi-directional
    soil_id = Column(INTEGER, ForeignKey("soil.id"))
    soil = relationship("Soil", back_populates="events")

    # event to plant: n:1, bi-directional
    plant_id = Column(INTEGER, ForeignKey("plants.id"), nullable=False)
    plant = relationship("Plant", back_populates="events")

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # 1:n relationship to the photo_file/event link table
    images = relationship(
        "Image",
        secondary="image_to_event_association",
        overlaps="events,image,image_to_event_associations,event",  # silence warnings
    )
    image_to_event_associations = relationship(
        "ImageToEventAssociation", back_populates="event", overlaps="events,images"
    )  # silence warnings
