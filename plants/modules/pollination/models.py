from __future__ import annotations

import logging
from datetime import datetime

import sqlalchemy
from sqlalchemy import (
    BOOLEAN,
    DATE,
    FLOAT,
    INTEGER,
    TEXT,
    VARCHAR,
    Column,
    Enum,
    ForeignKey,
    Identity,
    Numeric,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import DateTime

from plants.extensions.orm import Base
from plants.modules.pollination.enums import (
    FlorescenceStatus,
    FlowerColorDifferentiation,
    StigmaPosition,
)

logger = logging.getLogger(__name__)


class Florescence(Base):
    """Flowering period of a plant."""

    __tablename__ = "florescence"
    id: int = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    plant_id = Column(
        INTEGER, ForeignKey("plants.id"), nullable=False
    )  # table name is 'plants'
    plant = relationship(
        "Plant", back_populates="florescences"
    )  # class name is 'Plant'

    inflorescence_appearance_date = Column(
        DATE
    )  # todo rename to inflorescence_appeared_at
    branches_count = Column(INTEGER)
    flowers_count = Column(INTEGER)

    perianth_length = Column(Numeric(3, 1))  # cm; 3 digits, 1 decimal --> 0.1 .. 99.9
    perianth_diameter = Column(Numeric(2, 1))  # cm; 2 digits, 1 decimal --> 0.1 .. 9.9
    flower_color = Column(VARCHAR(7))  # hex color code, e.g. #f2f600
    flower_color_second = Column(VARCHAR(7))  # hex color code, e.g. #f2f600
    flower_colors_differentiation = Column(sqlalchemy.Enum(FlowerColorDifferentiation))
    stigma_position = Column(sqlalchemy.Enum(StigmaPosition))

    first_flower_opening_date = Column(DATE)  # todo renamed to first_flower_opened_at
    last_flower_closing_date = Column(DATE)  # todo renamed to last_flower_closed_at

    # FlorescenceStatus (inflorescence_appeared | flowering | finished)
    florescence_status = Column(Enum(FlorescenceStatus), nullable=False)

    # some redundancy! might be re-calculated from pollinations
    first_seed_ripening_date = Column(DATE)
    last_seed_ripening_date = Column(DATE)
    avg_ripening_time = Column(FLOAT)  # in days
    # todo via relationship: first_seed_ripe_date, last_seed_ripe_date,
    #  average_ripening_time

    comment = Column(
        TEXT
    )  # limited to max 40 chars in frontend, longer only for imported data

    last_update_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    last_update_context = Column(VARCHAR(30))
    creation_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    creation_context = Column(VARCHAR(30), nullable=False)

    # pollinations of this florescence (with plant as mother plant)
    pollinations = relationship(
        "Pollination",
        back_populates="florescence",
        foreign_keys="Pollination.florescence_id",
    )


class Pollination(Base):
    """pollination attempts of a plant
    note: we don't make a composite key of inflorence_id and pollen_donor_id because
    we might have multiple
    differing attempts to pollinate for the same inflorence and pollen donor"""

    __tablename__ = "pollination"
    id = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )

    florescence_id = Column(INTEGER, ForeignKey("florescence.id"))
    florescence = relationship(
        "Florescence", back_populates="pollinations", foreign_keys=[florescence_id]
    )

    # todo: make sure it is same as florescence.plant_id if available
    seed_capsule_plant_id = Column(INTEGER, ForeignKey("plants.id"), nullable=False)
    seed_capsule_plant = relationship("Plant", foreign_keys=[seed_capsule_plant_id])

    pollen_donor_plant_id = Column(INTEGER, ForeignKey("plants.id"), nullable=False)
    pollen_donor_plant = relationship(
        "Plant",  # back_populates="pollinations_as_donor_plant",
        foreign_keys=[pollen_donor_plant_id],
    )

    pollen_type = Column(
        VARCHAR(20), nullable=False
    )  # PollenType (fresh | frozen | unknown)
    pollen_quality = Column(
        VARCHAR(10), nullable=False
    )  # PollenQuality (good | bad | unknown)
    # location at the very moment of pollination attempt (Location (indoor | outdoor
    # | indoor_led | unknown))
    location = Column(VARCHAR(100), nullable=False)

    count = Column(INTEGER)

    pollination_timestamp = Column(DateTime(timezone=True))  # todo rename
    label_color = Column(VARCHAR(60))
    # PollinationStatus ( attempt | seed_capsule | seed | germinated | unknown
    # | self_pollinated )
    pollination_status = Column(VARCHAR(40), nullable=False)
    ongoing = Column(BOOLEAN, nullable=False)

    # first harvest in case of multiple harvests
    harvest_date = Column(DATE)
    seed_capsule_length = Column(FLOAT)  # mm
    seed_capsule_width = Column(FLOAT)  # mm
    seed_length = Column(FLOAT)  # mm
    seed_width = Column(FLOAT)  # mm
    seed_count = Column(INTEGER)
    seed_capsule_description = Column(TEXT)
    seed_description = Column(TEXT)
    # first_germination_date = Column(DATE)
    days_until_first_germination = Column(
        INTEGER
    )  # days from sowing seeds to first seed germinated
    first_seeds_sown = Column(INTEGER)
    first_seeds_germinated = Column(INTEGER)
    germination_rate = Column(FLOAT)

    comment = Column(TEXT)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    last_update_context = Column(VARCHAR(30))

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    creation_at_context = Column(VARCHAR(30), nullable=False)

    # todo via 1:n association table: plants
