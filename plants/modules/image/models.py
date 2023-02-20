import logging
from pathlib import PurePath
from datetime import datetime

from sqlalchemy import Column, INTEGER, VARCHAR, ForeignKey, TEXT, TIMESTAMP, Identity, DateTime
from sqlalchemy.orm import relationship

from plants import settings
from plants.extensions.orm import Base

logger = logging.getLogger(__name__)


class ImageKeyword(Base):
    """keywords tagged at images"""
    __tablename__ = 'image_keywords'
    image_id = Column(INTEGER, ForeignKey('image.id'), primary_key=True, nullable=False)
    keyword = Column(VARCHAR(100), primary_key=True, nullable=False)  # todo max 30 for new keywords

    image = relationship(
        "Image",
        back_populates="keywords"
    )


class ImageToPlantAssociation(Base):
    """plants tagged at images"""
    __tablename__ = 'image_to_plant_association'
    image_id = Column(INTEGER, ForeignKey('image.id'), primary_key=True, nullable=False)
    plant_id = Column(INTEGER, ForeignKey('plants.id'), primary_key=True, nullable=False)

    # silence warnings for deletions of associated entities (image has image_to_plant_association and plants)
    __mapper_args__ = {
        "confirm_deleted_rows": False,
    }

    image = relationship(
        "Image",
        back_populates="image_to_plant_associations",
        overlaps="images,plants"  # silence warnings
    )

    plant = relationship(
        "Plant",
        back_populates="image_to_plant_associations",
        overlaps="images,plants"  # silence warnings
    )

    def __repr__(self):
        return f'<ImageToPlantAssociation {self.image_id} {self.plant_id}>'


class Image(Base):
    """image paths"""
    # images themselves are stored in file system
    # this table is only used to link events to images
    __tablename__ = 'image'
    id = Column(INTEGER, Identity(start=1, cycle=True, always=False), primary_key=True, nullable=False)
    filename = Column(VARCHAR(150), unique=True, nullable=False)  # pseudo-key
    relative_path = Column(VARCHAR(240))  # relative path to the original image file incl. file name
    description = Column(VARCHAR(500))
    record_date_time = Column(TIMESTAMP, nullable=False)

    last_update = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Image {self.id} {self.filename}>'

    @property
    def absolute_path(self):
        return settings.paths.path_photos.parent.joinpath(PurePath(self.relative_path))  # todo what?

    keywords = relationship(
        "ImageKeyword",
        back_populates="image"
    )

    plants = relationship(
        "Plant",
        secondary='image_to_plant_association',
    )
    image_to_plant_associations = relationship("ImageToPlantAssociation",
                                               back_populates="image",
                                               overlaps="plants"  # silence warnings
                                               )

    # 1:n relationship to the image/event link table
    events = relationship(
        "Event",
        secondary='image_to_event_association'
    )
    image_to_event_associations = relationship("ImageToEventAssociation",
                                               back_populates="image",
                                               overlaps="events"  # silence warnings
                                               )

    # 1:n relationship to the image/taxon link table
    taxa = relationship(
        "Taxon",
        secondary='image_to_taxon_association',
        overlaps="image_to_taxon_associations,images"  # silence warnings
    )
    image_to_taxon_associations = relationship("ImageToTaxonAssociation",
                                               back_populates="image",
                                               overlaps="images,taxa"  # silence warnings
                                               )


class ImageToEventAssociation(Base):
    __tablename__ = 'image_to_event_association'
    image_id = Column(INTEGER, ForeignKey('image.id'), primary_key=True)
    event_id = Column(INTEGER, ForeignKey('event.id'), primary_key=True)

    # silence warnings for deletions of associated entities (image has image_to_event_association and events)
    __mapper_args__ = {
        "confirm_deleted_rows": False,
    }

    image = relationship('Image',
                         back_populates='image_to_event_associations',
                         overlaps="events"  # silence warnings
                         )
    event = relationship('Event',
                         back_populates='image_to_event_associations',
                         overlaps="events"  # silence warnings
                         )


class ImageToTaxonAssociation(Base):
    __tablename__ = 'image_to_taxon_association'
    image_id = Column(INTEGER, ForeignKey('image.id'), primary_key=True)
    taxon_id = Column(INTEGER, ForeignKey('taxon.id'), primary_key=True)

    description = Column(TEXT)

    # silence warnings for deletions of associated entities (image has image_to_taxa_association and taxa)
    __mapper_args__ = {
        "confirm_deleted_rows": False,
    }

    image = relationship('Image',
                         back_populates='image_to_taxon_associations',
                         overlaps="images,taxa"  # silence warnings
                         )
    taxon = relationship('Taxon',
                         back_populates='image_to_taxon_associations',
                         overlaps="images,taxa"  # silence warnings
                         )



