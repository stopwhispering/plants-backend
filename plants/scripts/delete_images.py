import logging

from sqlalchemy.orm import Session

from plants.dependencies import get_db
from plants.models.image_models import Image
from plants.util.logger_utils import configure_root_logger

configure_root_logger(log_severity_console=logging.INFO, log_severity_file=logging.DEBUG)

logger = logging.getLogger(__name__)


def _delete_images_with_keywords(db: Session, delete):
    image_ids = set(d[0] for d in delete)
    image_relative_paths = set(d[1] for d in delete)
    images_to_delete = db.query(Image).filter(Image.id.in_(image_ids)).all()

    # be sure not to delete the wrong image
    for image in images_to_delete:

        if image.relative_path not in image_relative_paths:
            logger.warning(f'Relative path not as supplied. Not deleting {image.id} {image.relative_path}.')
            continue

        if image.plants:
            plant_names = [p.plant_name for p in image.plants]
            logger.warning(f'Image still has plants. Not deleting {image.id} {image.relative_path} ({plant_names}).')
            continue

        if image.events:
            image_dates = [e.date for e in image.events]
            logger.warning(f'Image still has events. Not deleting {image.id} {image.relative_path} ({image_dates}).')
            continue

        if image.taxa:
            taxon_names = [t.name for t in image.taxa]
            logger.warning(f'Image still has taxa. Not deleting {image.id} {image.relative_path} ({taxon_names}).')
            continue

        if image.keywords:
            for kw in image.keywords:
                logger.info(f'Keyword: {[k.keyword for k in image.keywords]}')
                db.delete(kw)
        logger.info(f'Deleting {image.id} {image.relative_path}')
        db.delete(image)
    db.commit()


if __name__ == '__main__':
    delete = [
        (128, 'photos/original/uploaded/20191123_141337.jpg'),
        (221, 'photos/original/uploaded/DSC05645_resized.JPG'),
        (1514, 'photos/original/uploaded/20210710_202956_resized.jpg'),
        (7932, 'photos/original/DCIM/Google Takeouts 2015/20151213_204126.jpg'),

        (5184, 'photos/original/DCIM/Google Takeouts 2015/20151213_194156.jpg'),
        (6830, 'photos/original/DCIM/Google Takeouts 2015/20151213_194150.jpg'),
        (3471, 'photos/original/DCIM/Google Takeouts 2015/20151213_194145.jpg'),
        (6355, 'photos/original/DCIM/Google Takeouts 2015/20151213_194127.jpg'),
        ]
    _delete_images_with_keywords(next(get_db()), delete=delete)
