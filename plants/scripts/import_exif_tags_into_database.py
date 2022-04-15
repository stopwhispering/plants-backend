import logging
from collections import Counter

from sqlalchemy.orm import Session

from plants.dependencies import get_db
from plants.models.image_models import get_image_by_relative_path, create_image, Image, add_plants_to_image, \
    add_keywords_to_image
from plants.models.plant_models import Plant
from plants.deprecated.photo_directory import get_photo_directory, PhotoDirectory


# logging.basicConfig(level=logging.INFO)
from plants.util.logger_utils import configure_root_logger

configure_root_logger(log_severity_console=logging.INFO, log_severity_file=logging.DEBUG)

logger = logging.getLogger(__name__)


all_plants_names_not_found_in_db = []


def _add_plants(plant_names: list[str], db: Session, image: Image):
    plants = [Plant.get_plant_by_plant_name(plant_name=plant_name,
                                            db=db) for plant_name in plant_names]
    indices_not_found = [i for i, v in enumerate(plants) if v is None]
    if indices_not_found:
        plants = [p for p in plants if p is not None]
        plant_names_not_found = [plant_names[i] for i in indices_not_found]
        plant_names_not_found_new = [p for p in plant_names_not_found if p not in all_plants_names_not_found_in_db]
        if plant_names_not_found_new:
            all_plants_names_not_found_in_db.extend(plant_names_not_found_new)
            logger.warning(f'Plant Name(s) not found in db: {plant_names_not_found_new}')
    if plants:
        logger.info(f'Adding tags for {len(plants)} plants to {image.relative_path}.')
        add_plants_to_image(image=image, plants=plants, db=db)


def _import(photo_directory: PhotoDirectory, db: Session):
    for photo_file in photo_directory.photos:
        logger.info(photo_file.relative_path)
        logger.debug(photo_file.description)
        logger.debug(photo_file.keywords)
        logger.debug(photo_file.plants)
        logger.debug(photo_file.record_date_time)
        logger.debug(photo_file.relative_path_thumb)
        logger.debug(photo_file.absolute_path)
        logger.debug(photo_file.filename)
        image_db: Image = get_image_by_relative_path(relative_path=photo_file.relative_path, db=db)

        # create new image in db
        if not image_db:
            logger.debug(f'Adding to db: {photo_file.relative_path} with {len(photo_file.keywords)} keywords.')
            image_db = create_image(db=db,
                                    relative_path=photo_file.relative_path,
                                    record_date_time=photo_file.record_date_time,
                                    description=photo_file.description,
                                    keywords=photo_file.keywords)
            _add_plants(plant_names=photo_file.plants, db=db, image=image_db)

        # upate missing entries
        if photo_file.description != image_db.description and (photo_file.description or image_db.description):
            if not image_db.description:
                image_db.description = photo_file.description
                db.commit()
            else:
                logger.error(f'Different Descriptions (File/DB) for {image_db.relative_path}: '
                             f'{photo_file.description} / {image_db.description}. Doing nothing.')

        if photo_file.record_date_time != image_db.record_date_time:
            if not image_db.record_date_time:
                image_db.record_date_time = photo_file.record_date_time
                db.commit()
            else:
                logger.error(f'Different Record Dates (File/DB) for {image_db.relative_path}: '
                             f'{photo_file.record_date_time} / {image_db.record_date_time}. Doing nothing.')

        if photo_file.plants != [p.plant_name for p in image_db.plants]:
            image_db_plant_names = set(p.plant_name for p in image_db.plants)
            photo_file_plant_names = set(p for p in photo_file.plants)
            missing_plant_names_in_db = [p for p in photo_file_plant_names if p not in image_db_plant_names]
            if missing_plant_names_in_db:
                logger.debug(f'Missing plants in db for {photo_file.relative_path}: {missing_plant_names_in_db}. '
                             f'Adding them.')
                _add_plants(plant_names=missing_plant_names_in_db, db=db, image=image_db)
            missing_plant_names_in_file = [p for p in image_db_plant_names if p not in photo_file_plant_names]
            if missing_plant_names_in_file:
                logger.error(f'Missing plants in file for {photo_file.relative_path}: {missing_plant_names_in_file}. '
                             f'(file:{photo_file_plant_names}/db:{image_db_plant_names}). Doing nothing')

        photo_file.keywords = [k.strip() for k in photo_file.keywords]
        duplicate_keywords = [kw for kw, count in Counter(photo_file.keywords).items() if count > 1]
        if duplicate_keywords:
            new_keywords = list(set(photo_file.keywords))
            logger.warning(f'Found keyword duplicates for image {photo_file.relative_path}. Keywords in exif tags: '
                           f'{photo_file.keywords}. Assuming {new_keywords}.')
            photo_file.keywords = new_keywords
        if photo_file.keywords != [k.keyword for k in image_db.keywords]:
            image_db_keywords = set(k.keyword for k in image_db.keywords)
            photo_file_keywords = set(p for p in photo_file.keywords)
            missing_keywords_in_db = [p for p in photo_file_keywords if p not in image_db_keywords]
            if missing_keywords_in_db:
                logger.debug(f'Missing keywords in db for {photo_file.relative_path}: {missing_keywords_in_db}. '
                             f'Adding them.')
                add_keywords_to_image(image=image_db, keywords=missing_keywords_in_db, db=db)
            missing_keywords_in_file = [p for p in image_db_keywords if p not in photo_file_keywords]
            if missing_keywords_in_file:
                logger.error(f'Missing keywords in file for {photo_file.relative_path}: {missing_keywords_in_file}. '
                             f'(file:{photo_file_keywords}/db:{image_db_keywords}). Doing nothing.')


if __name__ == '__main__':
    photo_dir = get_photo_directory()
    logger.info(f'Photos Count in Photo Directory: {len(photo_dir.photos)}')
    _import(photo_dir, db=next(get_db()))
