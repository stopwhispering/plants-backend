import logging
from collections import Counter

from sqlalchemy.orm import Session

from plants.dependencies import get_db
from plants.models.image_models import Image, ImageToEventAssociation

# logging.basicConfig(level=logging.INFO)
from plants.util.logger_utils import configure_root_logger

configure_root_logger(log_severity_console=logging.INFO, log_severity_file=logging.DEBUG)

logger = logging.getLogger(__name__)

all_plants_names_not_found_in_db = []


def _find_duplicates_image_with_same_relative_path(db: Session):
    all_images: list[Image] = db.query(Image).all()
    all_image_relative_paths = [i.relative_path for i in all_images]
    counter = Counter(all_image_relative_paths)
    duplicate_paths = {key: value for key, value in counter.items() if value > 1}
    if not duplicate_paths:
        logger.info('No Duplicates')
        return

    map_relative_path_to_duplicates = {}
    for relative_path in duplicate_paths.keys():
        map_relative_path_to_duplicates[relative_path] = db.query(Image).filter(Image.relative_path
                                                                                == relative_path).all()
    all_duplicate_single_images = [i for image_list in map_relative_path_to_duplicates.values() for i in image_list]
    if any(i.taxa for i in all_duplicate_single_images):
        raise NotImplementedError

    add_list = []
    for releative_path, images in map_relative_path_to_duplicates.items():
        # 1. always use first image
        leading_image = images[0]
        for bad_image in images[1:]:
            for association_to_remove in bad_image.image_to_event_associations:

                # create same event association for leading image
                if not [a for a in leading_image.image_to_event_associations if
                        a.event_id == association_to_remove.event_id]:
                    new_association = ImageToEventAssociation(image_id=leading_image.id,
                                                              event_id=association_to_remove.event_id)
                    add_list.append(new_association)
                logger.info(f'Deleting {association_to_remove.event_id} / {association_to_remove.image_id}')
                db.delete(association_to_remove)
            db.delete(bad_image)

        db.add_all(add_list)
        db.commit()


if __name__ == '__main__':
    _find_duplicates_image_with_same_relative_path(db=next(get_db()))
