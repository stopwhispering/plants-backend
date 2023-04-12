from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

# import sqlalchemy
import sqlalchemy as sa
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
    Context,
    FlorescenceStatus,
    FlowerColorDifferentiation,
    Location,
    PollenQuality,
    PollenType,
    PollinationStatus,
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
    inflorescence_appeared_at: datetime.date | None = Column(DATE)
    branches_count = Column(INTEGER)
    flowers_count = Column(INTEGER)

    # cm; 3 digits, 1 decimal --> 0.1 .. 99.9
    perianth_length: Decimal | None = Column(Numeric(3, 1))  # type: ignore[misc]
    # cm; 2 digits, 1 decimal --> 0.1 .. 9.9
    perianth_diameter: Decimal | None = Column(Numeric(2, 1))  # type: ignore[misc]
    # hex color code, e.g. #f2f600
    flower_color: str | None = Column(VARCHAR(7))
    flower_color_second: str | None = Column(VARCHAR(7))
    flower_colors_differentiation: FlowerColorDifferentiation | None = Column(
        sa.Enum(FlowerColorDifferentiation)
    )
    stigma_position: StigmaPosition | None = Column(sa.Enum(StigmaPosition))

    first_flower_opened_at: datetime.date | None = Column(DATE)
    last_flower_closed_at: datetime.date | None = Column(DATE)

    # FlorescenceStatus (inflorescence_appeared | flowering | finished)
    florescence_status: FlorescenceStatus = Column(Enum(FlorescenceStatus), nullable=False)

    # some redundancy! might be re-calculated from pollinations
    first_seed_ripening_date: datetime.date | None = Column(DATE)
    last_seed_ripening_date: datetime.date | None = Column(DATE)
    # in days
    avg_ripening_time: float | None = Column(FLOAT)  # type:ignore[misc]

    # limited to max 40 chars in frontend, longer only for imported data
    comment: str | None = Column(TEXT)

    last_update_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)
    last_update_context = Column(Enum(Context))
    creation_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    creation_context = Column(Enum(Context), nullable=False)

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
    # noinspection PyTypeChecker
    florescence: Mapped[Florescence | None] = relationship(
        "Florescence", back_populates="pollinations", foreign_keys=[florescence_id]
    )

    seed_capsule_plant_id: int = Column(INTEGER, ForeignKey("plants.id"), nullable=False)
    # noinspection PyTypeChecker
    seed_capsule_plant: Mapped[Plant] = relationship("Plant", foreign_keys=[seed_capsule_plant_id])

    pollen_donor_plant_id: int = Column(INTEGER, ForeignKey("plants.id"), nullable=False)
    # noinspection PyTypeChecker
    pollen_donor_plant: Mapped[Plant] = relationship(
        "Plant",  # back_populates="pollinations_as_donor_plant",
        foreign_keys=[pollen_donor_plant_id],
    )

    # (fresh | frozen | unknown)
    pollen_type: PollenType = Column(sa.Enum(PollenType), nullable=False)
    # (good | bad | unknown)
    pollen_quality: PollenQuality = Column(sa.Enum(PollenQuality), nullable=False)
    # location at the very moment of pollination attempt
    # (indoor | outdoor | indoor_led | unknown)
    location: Location = Column(sa.Enum(Location), nullable=False)

    # count: int | None = Column(INTEGER)
    count_attempted: int | None = Column(INTEGER)  # attempted pollinations
    count_pollinated: int | None = Column(INTEGER)  # pollinated flowers
    count_capsules: int | None = Column(INTEGER)  # seed capsules

    pollinated_at = Column(DateTime(timezone=True))
    label_color: str | None = Column(VARCHAR(60))
    # ( attempt | seed_capsule | seed | germinated | unknown | self_pollinated )
    pollination_status: PollinationStatus = Column(sa.Enum(PollinationStatus), nullable=False)
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
    germination_rate: float | None = Column(FLOAT)  # type: ignore[misc]

    comment = Column(TEXT)

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)
    last_update_context = Column(Enum(Context))

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    creation_at_context = Column(sa.Enum(Context), nullable=False)
