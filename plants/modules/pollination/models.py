from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

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
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.types import DateTime

from plants.extensions.orm import Base
from plants.modules.pollination.enums import (
    FlorescenceStatus,
    FlowerColorDifferentiation,
    StigmaPosition,
)

if TYPE_CHECKING:
    from decimal import Decimal

    from plants.modules.plant.models import Plant

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
    plant_id: int = Column(
        INTEGER, ForeignKey("plants.id"), nullable=False
    )  # table name is 'plants'
    plant: Mapped[Plant] = relationship(
        "Plant", back_populates="florescences"
    )  # class name is 'Plant'
    # todo rename to inflorescence_appeared_at
    inflorescence_appearance_date: datetime.date | None = Column(DATE)
    branches_count = Column(INTEGER)
    flowers_count = Column(INTEGER)

    # cm; 3 digits, 1 decimal --> 0.1 .. 99.9
    perianth_length: Decimal | None = Column(Numeric(3, 1))  # type:ignore
    # cm; 2 digits, 1 decimal --> 0.1 .. 9.9
    perianth_diameter: Decimal | None = Column(Numeric(2, 1))  # type:ignore
    # hex color code, e.g. #f2f600
    flower_color: str | None = Column(VARCHAR(7))
    flower_color_second: str | None = Column(VARCHAR(7))
    flower_colors_differentiation: FlowerColorDifferentiation | None = Column(
        sqlalchemy.Enum(FlowerColorDifferentiation)
    )
    stigma_position: StigmaPosition | None = Column(sqlalchemy.Enum(StigmaPosition))

    # todo renamed to first_flower_opened_at
    first_flower_opening_date: datetime.date | None = Column(DATE)
    # todo renamed to last_flower_closed_at
    last_flower_closing_date: datetime.date | None = Column(DATE)

    # FlorescenceStatus (inflorescence_appeared | flowering | finished)
    florescence_status: FlorescenceStatus = Column(
        Enum(FlorescenceStatus), nullable=False
    )

    # some redundancy! might be re-calculated from pollinations
    first_seed_ripening_date: datetime.date | None = Column(DATE)
    last_seed_ripening_date: datetime.date | None = Column(DATE)
    # in days
    avg_ripening_time: float | None = Column(FLOAT)  # type:ignore
    # todo via relationship: first_seed_ripe_date, last_seed_ripe_date,
    #  average_ripening_time

    # limited to max 40 chars in frontend, longer only for imported data
    comment: str | None = Column(TEXT)

    last_update_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)
    last_update_context = Column(VARCHAR(30))
    creation_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow
    )
    creation_context = Column(VARCHAR(30), nullable=False)

    # pollinations of this florescence (with plant as mother plant)
    pollinations: Mapped[list[Pollination]] = relationship(
        "Pollination",
        back_populates="florescence",
        foreign_keys="Pollination.florescence_id",
        uselist=True,
    )


class Pollination(Base):
    """pollination attempts of a plant
    note: we don't make a composite key of inflorence_id and pollen_donor_id because
    we might have multiple
    differing attempts to pollinate for the same inflorence and pollen donor"""

    __tablename__ = "pollination"
    id: int = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )

    florescence_id: int | None = Column(INTEGER, ForeignKey("florescence.id"))
    florescence: Mapped[Florescence | None] = relationship(
        "Florescence", back_populates="pollinations", foreign_keys=[florescence_id]
    )

    # todo: make sure it is same as florescence.plant_id if available
    seed_capsule_plant_id: int = Column(
        INTEGER, ForeignKey("plants.id"), nullable=False
    )
    seed_capsule_plant: Mapped[Plant] = relationship(
        "Plant", foreign_keys=[seed_capsule_plant_id]
    )

    pollen_donor_plant_id: int = Column(
        INTEGER, ForeignKey("plants.id"), nullable=False
    )
    pollen_donor_plant: Mapped[Plant] = relationship(
        "Plant",  # back_populates="pollinations_as_donor_plant",
        foreign_keys=[pollen_donor_plant_id],
    )

    pollen_type: str = Column(
        VARCHAR(20), nullable=False
    )  # PollenType (fresh | frozen | unknown)
    pollen_quality: str = Column(
        VARCHAR(10), nullable=False
    )  # PollenQuality (good | bad | unknown)
    # location at the very moment of pollination attempt (Location (indoor | outdoor
    # | indoor_led | unknown))
    location: str = Column(VARCHAR(100), nullable=False)

    count: int | None = Column(INTEGER)

    pollination_timestamp = Column(DateTime(timezone=True))  # todo rename
    label_color: str | None = Column(VARCHAR(60))
    # PollinationStatus ( attempt | seed_capsule | seed | germinated | unknown
    # | self_pollinated )
    pollination_status: str = Column(VARCHAR(40), nullable=False)
    ongoing: bool = Column(BOOLEAN, nullable=False)

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

    last_update = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)
    last_update_context = Column(VARCHAR(30))

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow
    )
    creation_at_context = Column(VARCHAR(30), nullable=False)

    # todo via 1:n association table: plants
