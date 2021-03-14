from sqlalchemy import Column, INTEGER, CHAR, ForeignKey, TEXT
from sqlalchemy.orm import relationship

from plants.extensions.db import Base


class Image(Base):
    """image paths"""
    # images themselves are stored in file system and their information in exif tags
    # this table is only used to link events to images
    __tablename__ = 'image'
    id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
    relative_path = Column(CHAR(240))  # relative path to the original image file incl. file name  # pseudo-key

    # 1:n relationship to the image/event link table
    events = relationship(
            "Event",
            secondary='image_to_event_association'
            )
    image_to_event_associations = relationship("ImageToEventAssociation", back_populates="image")

    # 1:n relationship to the image/taxon link table
    taxa = relationship(
            "Taxon",
            secondary='image_to_taxon_association'
            )
    image_to_taxon_associations = relationship("ImageToTaxonAssociation", back_populates="image")


class ImageToEventAssociation(Base):
    __tablename__ = 'image_to_event_association'
    image_id = Column(INTEGER, ForeignKey('image.id'), primary_key=True)
    event_id = Column(INTEGER, ForeignKey('event.id'), primary_key=True)

    image = relationship('Image', back_populates='image_to_event_associations')
    event = relationship('Event', back_populates='image_to_event_associations')


class ImageToTaxonAssociation(Base):
    __tablename__ = 'image_to_taxon_association'
    image_id = Column(INTEGER, ForeignKey('image.id'), primary_key=True)
    taxon_id = Column(INTEGER, ForeignKey('taxon.id'), primary_key=True)

    description = Column(TEXT)

    image = relationship('Image', back_populates='image_to_taxon_associations')
    taxon = relationship('Taxon', back_populates='image_to_taxon_associations')
