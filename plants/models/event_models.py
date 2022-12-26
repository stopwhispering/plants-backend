from __future__ import annotations

from datetime import datetime
from typing import List
from sqlalchemy import Column, INTEGER, ForeignKey, TEXT, Identity, VARCHAR, DateTime
from sqlalchemy.orm import relationship, Session
import logging

from plants.util.ui_utils import throw_exception
from plants.util.OrmUtilMixin import OrmUtil
from plants.extensions.db import Base

logger = logging.getLogger(__name__)


class Soil(Base, OrmUtil):
    __tablename__ = "soil"
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    soil_name = Column(VARCHAR(100), nullable=False)
    description = Column(TEXT)
    mix = Column(TEXT)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # 1:n relationship to events (no need for bidirectional relationship)
    events = relationship("Event", back_populates="soil")


class Pot(Base, OrmUtil):
    __tablename__ = "pot"
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    material = Column(VARCHAR(50))
    shape_top = Column(VARCHAR(20))  # oval, square, circle
    shape_side = Column(VARCHAR(20))  # flat, very flat, high, very high
    diameter_width = Column(INTEGER)  # in mm
    # pot_notes = Column(TEXT)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # 1:n relationship to events
    events = relationship("Event", back_populates="pot")


class Observation(Base, OrmUtil):
    """formerly: Measurement"""
    __tablename__ = 'observation'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    # plant_name = Column(VARCHAR(60), nullable=False)
    diseases = Column(TEXT)
    stem_max_diameter = Column(INTEGER)  # stem or caudex (max) in mm
    height = Column(INTEGER)  # in mm
    # location = Column(VARCHAR(30))
    observation_notes = Column(TEXT)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # 1:1 relationship to event
    event = relationship("Event", back_populates="observation", uselist=False)


class Event(Base, OrmUtil):
    """events"""
    __tablename__ = 'event'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    date = Column(VARCHAR(12), nullable=False)  # e.g. 201912241645 or 201903
    event_notes = Column(TEXT)

    # 1:1 relationship to observation (joins usually from event to observation, not the other way around)
    observation_id = Column(INTEGER, ForeignKey('observation.id'))
    observation = relationship("Observation", back_populates="event")

    # n:1 relationship to pot, bi-directional
    pot_id = Column(INTEGER, ForeignKey('pot.id'))
    pot = relationship("Pot", back_populates="events")

    # n:1 relationship to soil, bi-directional
    soil_id = Column(INTEGER, ForeignKey('soil.id'))
    soil = relationship("Soil", back_populates="events")

    # event to plant: n:1, bi-directional
    plant_id = Column(INTEGER, ForeignKey('plants.id'), nullable=False)
    plant = relationship("Plant", back_populates="events")

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # 1:n relationship to the photo_file/event link table
    images = relationship(
            "Image",
            secondary='image_to_event_association',
            overlaps="events,image,image_to_event_associations,event"  # silence warnings
            )
    image_to_event_associations = relationship("ImageToEventAssociation",
                                               back_populates="event",
                                               overlaps="events,images")  # silence warnings

    def as_dict(self):
        """add some additional fields to mixin's as_dict, especially from relationships"""
        as_dict = super(Event, self).as_dict()

        # delete db foreign keys not meant for frontend usage
        del as_dict['soil_id']
        del as_dict['pot_id']
        del as_dict['observation_id']

        # read segments from their respective linked tables
        if self.observation:
            as_dict['observation'] = self.observation.as_dict()
            if as_dict['observation'].get('height'):
                as_dict['observation']['height'] = as_dict['observation']['height'] / 10  # mm to cm
            if as_dict['observation'].get('stem_max_diameter'):
                as_dict['observation']['stem_max_diameter'] = as_dict['observation']['stem_max_diameter'] / 10
        else:
            as_dict['observation'] = None

        if self.pot:
            as_dict['pot'] = self.pot.as_dict()
            if as_dict['pot'].get('diameter_width'):
                as_dict['pot']['diameter_width'] = as_dict['pot']['diameter_width'] / 10
        else:
            as_dict['pot'] = None

        if self.soil:
            as_dict['soil'] = self.soil.as_dict()
        else:
            as_dict['soil'] = None

        if self.images:
            as_dict['images'] = []
            for image_obj in self.images:
                # path_small = get_thumbnail_relative_path_for_relative_path(PurePath(image_obj.relative_path),
                #                                                            size=config.size_thumbnail_image)
                as_dict['images'].append({'id':            image_obj.id,
                                          'filename':      image_obj.filename,
                                          # 'relative_path': image_obj.relative_path
                                          })
        else:
            as_dict['images'] = []

        return as_dict

    # static query methods
    @staticmethod
    def get_events_by_plant_id(plant_id: int,
                               db: Session,
                               raise_exception: bool = False) -> List[Event]:
        events = db.query(Event).filter(Event.plant_id == plant_id).all()
        if not events and raise_exception:
            throw_exception(f'No events in db for plant: {plant_id}')
        return events

    @staticmethod
    def get_event_by_event_id(event_id: int,
                              db: Session,
                              raise_exception: bool = False) -> Event:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event and raise_exception:
            throw_exception(f'Event not found in db: {event_id}')
        return event
