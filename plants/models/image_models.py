import logging
from pathlib import PurePath
from datetime import datetime
from typing import Sequence

from sqlalchemy import Column, INTEGER, VARCHAR, ForeignKey, TEXT, TIMESTAMP, Identity, DateTime
from sqlalchemy.orm import relationship, Session

from plants import config
from plants.extensions.db import Base
from plants.models.plant_models import Plant
from plants.util.ui_utils import throw_exception

logger = logging.getLogger(__name__)


class ImageKeyword(Base):
    """keywords tagged at images"""
    __tablename__ = 'image_keywords'
    image_id = Column(INTEGER, ForeignKey('image.id'), primary_key=True, nullable=False)
    keyword = Column(VARCHAR(100), primary_key=True, nullable=False)

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

    @property
    def absolute_path(self):
        return config.path_photos_base.parent.joinpath(PurePath(self.relative_path))

    keywords: list[ImageKeyword] = relationship(
        "ImageKeyword",
        back_populates="image"
    )

    plants = relationship(
        "Plant",
        secondary='image_to_plant_association',
    )
    image_to_plant_associations: list = relationship("ImageToPlantAssociation",
                                                     back_populates="image",
                                                     overlaps="plants"  # silence warnings
                                                     )

    # 1:n relationship to the image/event link table
    events = relationship(
        "Event",
        secondary='image_to_event_association'
    )
    image_to_event_associations: list = relationship("ImageToEventAssociation",
                                                     back_populates="image",
                                                     overlaps="events"  # silence warnings
                                                     )

    # 1:n relationship to the image/taxon link table
    taxa = relationship(
        "Taxon",
        secondary='image_to_taxon_association',
        overlaps="image_to_taxon_associations,images"  # silence warnings
    )
    image_to_taxon_associations: list = relationship("ImageToTaxonAssociation",
                                                     back_populates="image",
                                                     overlaps="images,taxa"  # silence warnings
                                                     )

    @staticmethod
    def get_image_by_filename(filename: str, db: Session) -> "Image":
        """returns image by filename"""
        image = db.query(Image).filter(Image.filename == filename).first()
        if not image:
            logger.error(err_msg := f'Image not found in db: {filename}')
            throw_exception(err_msg)
        return image

    @staticmethod
    def get_image_by_id(id_: int, db: Session) -> "Image":
        """returns image by filename"""
        image = db.query(Image).filter(Image.id == id_).first()
        if not image:
            logger.error(err_msg := f'Image not found in db: {id_}')
            throw_exception(err_msg)
        return image

    @staticmethod
    def exists(filename: str, db: Session) -> bool:
        """returns True if image exists in db"""
        return db.query(Image).filter(Image.filename == filename).first() is not None


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


def get_image_by_relative_path(relative_path: PurePath, db: Session, raise_exception: bool = False) -> Image:
    image = db.query(Image).filter(Image.relative_path == relative_path.as_posix()).scalar()
    if not image and raise_exception:
        throw_exception(f'Image not found in database: {relative_path}')
    return image


def add_plants_to_image(db: Session,
                        image: Image,
                        plants: list[Plant] = ()):
    image.plants = plants
    db.commit()


def add_keywords_to_image(db: Session, image: Image, keywords: Sequence[str]):
    _ = [ImageKeyword(
        image_id=image.id,
        image=image,
        keyword=k) for k in keywords]

    db.commit()


def create_image(db: Session,
                 relative_path: PurePath,
                 record_date_time: datetime,
                 description: str = None,
                 plants: list[Plant] = None,
                 keywords: Sequence[str] = (),
                 # events and taxa are saved elsewhere
                 ) -> Image:
    if db.query(Image).filter(Image.relative_path == relative_path.as_posix()).first():
        raise ValueError(f'Image already exists in db: {relative_path.as_posix()}')

    image = Image(relative_path=relative_path.as_posix(),
                  filename=relative_path.name,
                  record_date_time=record_date_time,
                  description=description,
                  # last_update=datetime.now(),
                  # created_at=datetime.now(),
                  plants=plants if plants else [],
                  )
    # get the image id
    db.add(image)
    db.flush()

    if keywords:
        add_keywords_to_image(image=image, keywords=keywords, db=db)

    db.commit()
    return image


def update_image_if_altered(db: Session,
                            image: Image,
                            description: str,
                            plant_ids: Sequence[int],
                            keywords: Sequence[str],
                            ):
    """compare current database record for image with supplied field values; update db entry if different;
    Note: record_date_time is only set at upload, so we're not comparing or updating it."""
    # description
    if description != image.description and not (not description and not image.description):
        image.description = description
        # image.last_update = datetime.now()

    # plants
    new_plants = set(Plant.get_plant_by_plant_id(plant_id, db=db, raise_exception=True) for plant_id in plant_ids)
    removed_image_to_plant_associations = [a for a in image.image_to_plant_associations
                                           if a.plant not in new_plants]
    added_image_to_plant_associations = [ImageToPlantAssociation(
        image=image,
        plant=p, )
        for p in new_plants if p not in image.plants]
    for removed_image_to_plant_association in removed_image_to_plant_associations:
        db.delete(removed_image_to_plant_association)
    if added_image_to_plant_associations:
        image.image_to_plant_associations.extend(added_image_to_plant_associations)

    # keywords
    current_keywords = set(k.keyword for k in image.keywords)
    removed_keywords = [k for k in image.keywords if k.keyword not in keywords]
    added_keywords = [ImageKeyword(image_id=image.id,
                                   keyword=k)
                      for k in set(keywords) if k not in current_keywords]

    for removed_keyword in removed_keywords:
        db.delete(removed_keyword)
    if added_keywords:
        image.keywords.extend(added_keywords)
    db.commit()
