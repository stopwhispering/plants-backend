from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import Column, VARCHAR, INTEGER, ForeignKey, TEXT, DATE, FLOAT, BOOLEAN, Identity, Numeric
import sqlalchemy

from sqlalchemy.types import DateTime
import logging

from sqlalchemy.orm import relationship, Session

from plants.shared.message_services import throw_exception
from plants.shared.orm_utils import OrmAsDict
from plants.extensions.orm import Base

logger = logging.getLogger(__name__)


# keep in sync with formatter.js in frontend
class PollinationStatus(str, enum.Enum):
    ATTEMPT = "attempt"
    SEED_CAPSULE = "seed_capsule"
    SEED = "seed"
    GERMINATED = "germinated"
    UNKNOWN = "unknown"
    SELF_POLLINATED = "self_pollinated"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class PollenType(str, enum.Enum):
    FRESH = "fresh"
    FROZEN = "frozen"
    UNKNOWN = "unknown"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class Context(str, enum.Enum):
    IMPORT = "import"
    MANUAL = "manual"  # manual db corrections
    API = "api"  # api calls from frontend


class Location(str, enum.Enum):
    UNKNOWN = "unknown"
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    INDOOR_LED = "indoor_led"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


COLORS_MAP: dict[str, str] = {
    '#f2f600': 'yellow',
    '#d21d26': 'red',
    '#ffffff': 'white',
    '#f5bfd9': 'pale rose',
    '#9a5abf': 'purple',
    '#008b3c': 'green',
    '#ff7c09': 'orange',
    '#16161b': 'black',
    '#909090': 'gray',
    '#6b492b': 'brown',
    '#104e8b': 'dark blue',
    '#b0e2ff': 'light blue',
    '#46f953': 'neon green',
}

COLORS_MAP_TO_RGB = {v: k for k, v in COLORS_MAP.items()}


class BFlorescenceStatus(str, enum.Enum):
    INFLORESCENCE_APPEARED = "inflorescence_appeared"
    FLOWERING = "flowering"
    FINISHED = "finished"  # as soon as the last flower is closed

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class FlowerColorDifferentiation(str, enum.Enum):
    TOP_BOTTOM = "top_bottom"
    OVARY_MOUTH = "ovary_mouth"
    UNIFORM = "uniform"


class StigmaPosition(str, enum.Enum):
    EXSERTED = "exserted"
    MOUTH = "mouth"
    INSERTED = "inserted"
    DEEPLY_INSERTED = "deeply_inserted"


class Florescence(Base, OrmAsDict):
    """flowering period of a plant"""
    __tablename__ = 'florescence'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    plant_id = Column(INTEGER, ForeignKey('plants.id'), nullable=False)  # table name is 'plants'
    plant = relationship("Plant", back_populates="florescences")  # class name is 'Plant'

    inflorescence_appearance_date = Column(DATE)  # todo rename to inflorescence_appeared_at
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
    florescence_status = Column(VARCHAR(100))  # todo enum

    # some redundancy! might be re-calculated from pollinations
    first_seed_ripening_date = Column(DATE)
    last_seed_ripening_date = Column(DATE)
    avg_ripening_time = Column(FLOAT)  # in days
    # todo via relationship: first_seed_ripe_date, last_seed_ripe_date, average_ripening_time

    comment = Column(TEXT)  # limited to max 40 chars in frontend, longer only for imported data

    last_update_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    last_update_context = Column(VARCHAR(30))
    creation_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    creation_context = Column(VARCHAR(30), nullable=False)

    # pollinations of this florescence (with plant as mother plant)
    pollinations = relationship("Pollination",
                                back_populates="florescence",
                                foreign_keys="Pollination.florescence_id")

    def as_dict(self):
        """add some additional fields to mixin's as_dict"""
        as_dict = super(Florescence, self).as_dict()
        as_dict['plant_name'] = (self.plant.plant_name
                                 if self.plant else None)
        return as_dict

    @staticmethod
    def by_id(florescence_id: int, db: Session, raise_exception: bool = True) -> Florescence | None:
        florescence = db.query(Florescence).filter(Florescence.id == florescence_id).first()
        if not florescence and raise_exception:
            throw_exception(f'Florescence ID not found in database: {florescence_id}')
        return florescence


class Pollination(Base, OrmAsDict):
    """pollination attempts of a plant
    note: we don't make a composite key of inflorence_id and pollen_donor_id because we might have multiple
    differing attempts to pollinate for the same inflorence and pollen donor"""
    __tablename__ = 'pollination'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)

    florescence_id = Column(INTEGER, ForeignKey('florescence.id'))
    florescence = relationship("Florescence", back_populates="pollinations", foreign_keys=[florescence_id])

    # todo: make sure it is same as florescence.plant_id if available
    seed_capsule_plant_id = Column(INTEGER, ForeignKey('plants.id'), nullable=False)
    seed_capsule_plant = relationship("Plant", foreign_keys=[seed_capsule_plant_id])

    pollen_donor_plant_id = Column(INTEGER, ForeignKey('plants.id'), nullable=False)
    pollen_donor_plant = relationship("Plant",  # back_populates="pollinations_as_donor_plant",
                                      foreign_keys=[pollen_donor_plant_id])

    pollen_type = Column(VARCHAR(20), nullable=False)  # PollenType (fresh | frozen | unknown)
    # location at the very moment of pollination attempt (Location (indoor | outdoor | indoor_led | unknown))
    location = Column(VARCHAR(100), nullable=False)

    count = Column(INTEGER)

    pollination_timestamp = Column(DateTime(timezone=True))  # todo rename
    label_color = Column(VARCHAR(60))
    # PollinationStatus ( attempt | seed_capsule | seed | germinated | unknown | self_pollinated )
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
    days_until_first_germination = Column(INTEGER)  # days from sowing seeds to first seed germinated
    first_seeds_sown = Column(INTEGER)
    first_seeds_germinated = Column(INTEGER)
    germination_rate = Column(FLOAT)

    comment = Column(TEXT)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    last_update_context = Column(VARCHAR(30))

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    creation_at_context = Column(VARCHAR(30), nullable=False)

    # todo via 1:n association table: plants

    def as_dict(self):
        """add some additional fields to mixin's as_dict"""
        as_dict = super(Pollination, self).as_dict()
        as_dict['seed_capsule_plant_name'] = (self.seed_capsule_plant.plant_name
                                              if self.seed_capsule_plant else None)
        as_dict['pollen_donor_plant_name'] = (self.pollen_donor_plant.plant_name
                                              if self.pollen_donor_plant else None)
        return as_dict
