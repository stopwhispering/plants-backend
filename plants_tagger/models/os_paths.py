import os
from plants_tagger.config_local import PATH_BASE, SUBDIRECTORY_PHOTOS, PATH_DELETED_PHOTOS

if os.name == 'nt':
    SUBDIRECTORY_PHOTOS_SEARCH = SUBDIRECTORY_PHOTOS + '\\'
else:
    SUBDIRECTORY_PHOTOS_SEARCH = SUBDIRECTORY_PHOTOS + r'/'

PATH_PHOTOS_BASE = os.path.join(PATH_BASE, SUBDIRECTORY_PHOTOS)
REL_PATH_PHOTOS_ORIGINAL = os.path.join(SUBDIRECTORY_PHOTOS, "original")
REL_PATH_PHOTOS_GENERATED = os.path.join(SUBDIRECTORY_PHOTOS, "generated")
PATH_GENERATED_THUMBNAILS = os.path.join(PATH_PHOTOS_BASE, 'generated')
PATH_ORIGINAL_PHOTOS = os.path.join(PATH_PHOTOS_BASE, 'original')
PATH_ORIGINAL_PHOTOS_UPLOADED = os.path.join(PATH_ORIGINAL_PHOTOS, 'uploaded')

# create folders if not existing
for path in [PATH_BASE, PATH_DELETED_PHOTOS, PATH_PHOTOS_BASE, PATH_GENERATED_THUMBNAILS, PATH_ORIGINAL_PHOTOS,
             PATH_ORIGINAL_PHOTOS_UPLOADED]:
    if not os.path.exists(path):
        os.makedirs(path)

# PATH_PHOTOS_BASE = r"C:\IDEs\sap-webide-personal-edition-1.53.9-trial-win32.win32.x86_64\serverworkspace\my\myuser" \
#                    r"\OrionContent\plants_tagger\webapp\localService"

# REL_PATH_PHOTOS_ORIGINAL = r"localService\original"
# REL_PATH_PHOTOS_GENERATED = r"localService\generated"

# PATH_ORIGINAL_PHOTOS_UPLOADED = r'C:\IDEs\sap-webide-personal-edition-1.53.9-trial-win32.win32.x86_64' \
#                                 r'\serverworkspace\my\myuser\OrionContent\plants_tagger\webapp\localService' \
#                                 r'\original\uploaded'
