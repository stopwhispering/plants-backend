import os

from plants import config

if os.name == 'nt':
    SUBDIRECTORY_PHOTOS_SEARCH = config.subdirectory_photos + '\\'
else:
    SUBDIRECTORY_PHOTOS_SEARCH = config.subdirectory_photos + r'/'

PATH_PHOTOS_BASE = os.path.join(config.path_base, config.subdirectory_photos)

REL_PATH_PHOTOS_ORIGINAL = os.path.join(config.subdirectory_photos, "original")
REL_PATH_PHOTOS_GENERATED = os.path.join(config.subdirectory_photos, "generated")
REL_PATH_PHOTOS_GENERATED_TAXON = os.path.join(config.subdirectory_photos, "generated_taxon")

PATH_GENERATED_THUMBNAILS = os.path.join(PATH_PHOTOS_BASE, 'generated')
PATH_GENERATED_THUMBNAILS_TAXON = os.path.join(PATH_PHOTOS_BASE, 'generated_taxon')

PATH_ORIGINAL_PHOTOS = os.path.join(PATH_PHOTOS_BASE, 'original')
PATH_ORIGINAL_PHOTOS_UPLOADED = os.path.join(PATH_ORIGINAL_PHOTOS, 'uploaded')

# create folders if not existing
for path in [config.path_base, config.path_deleted_photos, PATH_PHOTOS_BASE, PATH_GENERATED_THUMBNAILS,
             PATH_GENERATED_THUMBNAILS_TAXON, PATH_ORIGINAL_PHOTOS, PATH_ORIGINAL_PHOTOS_UPLOADED]:
    if not os.path.exists(path):
        os.makedirs(path)
