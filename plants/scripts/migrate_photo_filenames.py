# <<manually>> add filename as CHAR(150) (non-null, unique) column to image table

import pickle  # noqa
from pathlib import Path, PurePath

from sqlalchemy.orm import Session

from plants import config
from plants.dependencies import get_db
from plants.extensions.db import init_database_tables, engine
from plants.models.image_models import Image
from plants.models.plant_models import Plant
from plants.util.image_utils import generate_thumbnail, get_thumbnail_name

init_database_tables(engine_=engine)
db = next(get_db())


def remove_path_prefixes_from_filename(db):
    filename_to_plant = {}
    plants = db.query(Plant).filter(Plant.filename_previewimage != None).all()  # noqa
    for plant in plants:
        path = Path(plant.filename_previewimage)

        if path.name in filename_to_plant:
            print(f'filename already exists: {path.name}')
            print(plant.filename_previewimage, plant.plant_name)
            old = filename_to_plant[path.name]
            print(old.filename_previewimage, old.plant_name)

        filename_to_plant[path.name] = plant

        plant.filename_previewimage = path.name

    db.commit()


def fill_image_filename(db):
    max_size = 0
    images: list[Image] = db.query(Image).all()
    for image in images:
        filename = PurePath(image.relative_path).name
        image.filename = filename
        if len(filename) > max_size:
            max_size = len(filename)
            print(max_size, filename)
        # print(filename)
    print(f'Max Size: {max_size}')
    db.commit()


def generate_missing_thumbnails(db: Session):
    count_already_exists = 0
    count_generated = 0
    images: list[Image] = db.query(Image).all()
    for image in (i for i in images if i.absolute_path.is_file()):
        image: Image
        for size in config.sizes:
            path_thumbnail = config.path_generated_thumbnails.joinpath(get_thumbnail_name(image.filename, size))
            if path_thumbnail.is_file():
                count_already_exists += 1
            else:
                generate_thumbnail(image=image.absolute_path,
                                   size=size,
                                   path_thumbnail=config.path_generated_thumbnails)
                count_already_exists += 1
                print(f'Generated thumbnail in size {size} for {image.absolute_path}')

    print('Count already existed:', count_already_exists)
    print('Count generated:', count_generated)


# remove_path_prefixes_from_filename(db=db)
# fill_image_filename(db=db)
generate_missing_thumbnails(db=db)
