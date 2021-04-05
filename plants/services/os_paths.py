import os
from plants.config_local import PATH_BASE, SUBDIRECTORY_PHOTOS, PATH_DELETED_PHOTOS

if os.name == 'nt':
    SUBDIRECTORY_PHOTOS_SEARCH = SUBDIRECTORY_PHOTOS + '\\'
else:
    SUBDIRECTORY_PHOTOS_SEARCH = SUBDIRECTORY_PHOTOS + r'/'

PATH_PHOTOS_BASE = os.path.join(PATH_BASE, SUBDIRECTORY_PHOTOS)

REL_PATH_PHOTOS_ORIGINAL = os.path.join(SUBDIRECTORY_PHOTOS, "original")
REL_PATH_PHOTOS_GENERATED = os.path.join(SUBDIRECTORY_PHOTOS, "generated")
REL_PATH_PHOTOS_GENERATED_TAXON = os.path.join(SUBDIRECTORY_PHOTOS, "generated_taxon")

PATH_GENERATED_THUMBNAILS = os.path.join(PATH_PHOTOS_BASE, 'generated')
PATH_GENERATED_THUMBNAILS_TAXON = os.path.join(PATH_PHOTOS_BASE, 'generated_taxon')

PATH_ORIGINAL_PHOTOS = os.path.join(PATH_PHOTOS_BASE, 'original')
PATH_ORIGINAL_PHOTOS_UPLOADED = os.path.join(PATH_ORIGINAL_PHOTOS, 'uploaded')

# create folders if not existing
for path in [PATH_BASE, PATH_DELETED_PHOTOS, PATH_PHOTOS_BASE, PATH_GENERATED_THUMBNAILS,
             PATH_GENERATED_THUMBNAILS_TAXON, PATH_ORIGINAL_PHOTOS, PATH_ORIGINAL_PHOTOS_UPLOADED]:
    if not os.path.exists(path):
        os.makedirs(path)