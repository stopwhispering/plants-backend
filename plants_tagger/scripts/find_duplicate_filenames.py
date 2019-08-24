import os
import glob
import collections

import plants_tagger.config_local
from plants_tagger import config
from plants_tagger.util.exif_helper import modified_date, set_modified_date


def get_duplicate_filenames():
    folder = os.path.join(plants_tagger.config_local.path_frontend_temp,
                          plants_tagger.config_local.rel_folder_photos_original)
    # folder = folder + '\\'
    paths = glob.glob(folder + '/**/*.jp*g', recursive=True)
    files = [{'path': path_full,
              'filename': os.path.basename(path_full)} for path_full in paths]
    filenames = [os.path.basename(path) for path in paths]

    duplicates = [item for item, count in collections.Counter(filenames).items() if count > 1]
    results = {}
    for d in duplicates:
        results[d] = [f['path'] for f in files if f['filename'] == d]

    return results


def rename_duplicates(duplicates: dict):
    for key, values in duplicates.items():
        num = len(values) - 1
        for i in range(num):

            modified_time_seconds = modified_date(values[i])  # seconds

            folder = os.path.dirname(values[i])

            filename_list = key.split('.')
            filename_list.insert(-1, f'_{i}')
            filename_new = ".".join(filename_list)

            path_new = os.path.join(folder, filename_new)
            os.rename(values[i], path_new)

            # keep changed time
            set_modified_date(path_new, modified_time_seconds)


duplicates = get_duplicate_filenames()
rename_duplicates(duplicates)