# <<manually>> add filename as CHAR(150) (non-null, unique) column to image table

import pickle  # noqa
from pathlib import Path, PurePath

from plants.dependencies import get_db
from plants.extensions.db import init_database_tables, engine
from plants.models.image_models import Image
from plants.models.plant_models import Plant


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


remove_path_prefixes_from_filename(db=db)
fill_image_filename(db=db)
