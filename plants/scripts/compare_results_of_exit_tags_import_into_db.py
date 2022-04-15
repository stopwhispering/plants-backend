import json

from plants.dependencies import get_db
from plants.routers.functions import compare_images_in_db_with_exif_tags


def compare():

    results = compare_images_in_db_with_exif_tags(next(get_db()))
    json_string = json.dumps(results)
    with open('/common/_temp_comparison_results_db_exif.json', 'w') as outfile:
        outfile.write(json_string)


if __name__ == '__main__':
    compare()

