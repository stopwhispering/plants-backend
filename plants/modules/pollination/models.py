from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import pytz

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
    COLORS_MAP_TO_RGB,
    Context,
    FlorescenceStatus,
    FlowerColorDifferentiation,
    Location,
    PollenQuality,
    PollenType,
    PollinationStatus,
    SeedPlantingStatus,
    StigmaPosition,
)
from plants.modules.pollination.mappings import LOCATION_TEXTS
from plants.modules.pollination.prediction.predict_germination import (
    predict_germination_days,
    predict_germination_probability,
)

if TYPE_CHECKING:
    from decimal import Decimal

    from plants.modules.event.models import Soil
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

    self_pollinated = Column(BOOLEAN)

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

    @property
    def estimated_last_flower_closed_at(self) -> datetime.date | None:
        if self.last_flower_closed_at is not None:
            return self.last_flower_closed_at
        if self.first_flower_opened_at is not None:
            return self.first_flower_opened_at + datetime.timedelta(
                days=30
            )  # assume 30 days of flowering
        if self.inflorescence_appeared_at is not None:
            return self.inflorescence_appeared_at + datetime.timedelta(days=70)
        return None


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

    # optional only for imported data
    florescence_id: int | None = Column(INTEGER, ForeignKey("florescence.id"))
    # noinspection PyTypeChecker
    florescence: Mapped[Florescence | None] = relationship(  # None only for historical
        "Florescence",
        back_populates="pollinations",
        foreign_keys=[florescence_id],
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
    seed_plantings: Mapped[list[SeedPlanting]] = relationship(
        "SeedPlanting", back_populates="pollination"
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

    comment = Column(TEXT)

    last_updated_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)
    last_update_context = Column(Enum(Context))

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    creation_at_context = Column(sa.Enum(Context), nullable=False)

    def __repr__(self) -> str:
        return f"<Pollination {self.id} ({self.pollination_status}, harvested {self.harvest_date})>"

    @property
    def current_ripening_days(self) -> int:
        if not self.pollinated_at:
            return 0

        delta = (
            datetime.datetime.now(tz=pytz.timezone("Europe/Berlin")).date()
            - self.pollinated_at.date()
        )
        return delta.days if delta.days > 0 else 0

    @property
    def florescence_comment(self) -> str | None:
        return self.florescence.comment if self.florescence else None

    @property
    def location_text(self) -> str:
        return LOCATION_TEXTS[self.location]

    @property
    def pollen_donor_plant_preview_image_id(self) -> int | None:
        return self.pollen_donor_plant.preview_image_id

    @property
    def pollen_donor_plant_name(self) -> str:
        return self.pollen_donor_plant.plant_name

    @property
    def seed_capsule_plant_preview_image_id(self) -> int | None:
        return self.seed_capsule_plant.preview_image_id

    @property
    def seed_capsule_plant_name(self) -> str:
        return self.seed_capsule_plant.plant_name

    @property
    def label_color_rgb(self) -> str | None:
        if self.label_color:
            return COLORS_MAP_TO_RGB.get(self.label_color.lower(), "transparent")
        return None


class SeedPlanting(Base):
    """Planting attempt of a seed, possibly from Pollination."""

    __tablename__ = "seed_planting"
    id: int = Column(
        INTEGER,
        Identity(start=1, cycle=True, always=False),
        primary_key=True,
        nullable=False,
    )
    status: SeedPlantingStatus = Column(sa.Enum(SeedPlantingStatus), nullable=False)
    pollination_id: int = Column(INTEGER, ForeignKey("pollination.id"), nullable=False)
    # noinspection PyTypeChecker
    pollination: Mapped[Pollination] = relationship(
        "Pollination", back_populates="seed_plantings", foreign_keys=[pollination_id]
    )
    # seed_name: str | None = Column(VARCHAR(60))  # free text, only filled if no pollination linked
    comment = Column(TEXT)

    sterilized = Column(BOOLEAN)  # e.g. treated with Chinosol, null only for imported data
    soaked = Column(BOOLEAN)  # in water, null only for imported data
    covered = Column(BOOLEAN)  # covered for greenhouse effect, null only for imported data

    planted_on: datetime.date = Column(DATE, nullable=False)
    germinated_first_on = Column(DATE)
    abandoned_on = Column(DATE)

    count_planted = Column(INTEGER)  # number of seeds planted, null only for imported data
    count_germinated = Column(INTEGER)  # number of seeds germinated

    soil_id = Column(INTEGER, ForeignKey("soil.id"))  # null only for imported data
    soil: Mapped[Soil | None] = relationship(
        "Soil", back_populates="seed_plantings", foreign_keys=[soil_id]
    )

    plants: Mapped[list[Plant]] = relationship(
        "Plant",
        back_populates="seed_planting",
        foreign_keys="Plant.seed_planting_id",
    )

    last_update_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.utcnow)
    creation_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)

    @property
    def seed_capsule_plant_name(self) -> str:
        return self.pollination.seed_capsule_plant.plant_name  # if self.pollination else ""

    @property
    def pollen_donor_plant_name(self) -> str:
        return self.pollination.pollen_donor_plant.plant_name  # if self.pollination else ""

    @property
    def soil_name(self) -> str:
        return self.soil.soil_name if self.soil is not None else ""  # type: ignore[union-attr]

    @property
    def predicted_germination_probability(self) -> int | None:
        if self.status == SeedPlantingStatus.PLANTED:
            return predict_germination_probability(self)
        return None

    @property
    def predicted_germination_days(self) -> int | None:
        if self.status == SeedPlantingStatus.PLANTED:
            return predict_germination_days(self)
        return None

    @property
    def current_germination_days(self) -> int | None:
        if self.status == SeedPlantingStatus.PLANTED:
            return (datetime.datetime.now(tz=pytz.timezone("CET")).date() - self.planted_on).days
        return None

    @property
    def germination_days(self) -> int | None:
        if (
            self.status == SeedPlantingStatus.GERMINATED
            and self.germinated_first_on
            and self.planted_on
        ):
            return (self.germinated_first_on - self.planted_on).days
        if self.status == SeedPlantingStatus.ABANDONED and self.planted_on and self.abandoned_on:
            return (self.abandoned_on - self.planted_on).days
        return None
