# import json
# import logging
#
# from sqlalchemy.orm import Session
#
# from plants.dependencies import get_db
# from plants.deprecated.photo_directory import PhotoFactoryDatabase, PhotoFactoryLocalFiles, Photo
# from plants.util.ui_utils import make_dict_values_json_serializable
#
# logger = logging.getLogger(__name__)
#
#
# def compare_images_in_db_with_exif_tags(db: Session):
#     photos_from_files = PhotoFactoryLocalFiles().make_photos()
#     photos_from_db = PhotoFactoryDatabase(db=db).make_photos()
#
#     # photo_file files lacking database entries
#     relative_paths_db = set(p_db.relative_path for p_db in photos_from_db)
#     p: Photo
#     missing_in_db = [p for p in photos_from_files if p.relative_path not in relative_paths_db]
#     logger.info(f'Count of photo_file files lacking database entries: {len(missing_in_db)}')
#
#     # orphaned database entries without corresponding files
#     relative_paths_files = set(p_file.relative_path for p_file in photos_from_files)
#     missing_in_files = [p for p in photos_from_db if p.relative_path not in relative_paths_files]
#     logger.info(f'Count of orphaned database entries without corresponding files: {len(missing_in_files)}')
#
#     intersection = relative_paths_db.intersection(relative_paths_files)
#     logger.info(f'Count of files with corresponding db entry: {len(intersection)}')
#
#     # asynchronous entries (different descriptions, record date, keywords, or plants)
#     different_descriptions = {}
#     different_record_dates = {}
#     different_keywords = {}
#     different_plants = {}
#     intersection_from_files = [p for p in photos_from_files if p.relative_path in intersection]
#     for photo_from_file in intersection_from_files:
#         photo_from_db = [p for p in photos_from_db if p.relative_path == photo_from_file.relative_path][0]
#         if (photo_from_file.description != photo_from_db.description
#                 and (photo_from_file.description or photo_from_db.description)):
#             different_descriptions[photo_from_file.relative_path.as_posix()] = {
#                 'file': photo_from_file.description,
#                 'db': photo_from_db.description
#                 }
#         if photo_from_file.record_date_time != photo_from_db.record_date_time:
#             different_record_dates[photo_from_file.relative_path.as_posix()] = {
#                 'file': photo_from_file.record_date_time,
#                 'db': photo_from_db.record_date_time
#                 }
#         if set(photo_from_file.plants) != set(photo_from_db.plants):
#             different_plants[photo_from_file.relative_path.as_posix()] = {
#                 'file': photo_from_file.plants,
#                 'db': photo_from_db.plants
#                 }
#         if set(photo_from_file.keywords) != set(photo_from_db.keywords):
#             different_keywords[photo_from_file.relative_path.as_posix()] = {
#                 'file': photo_from_file.keywords,
#                 'db': photo_from_db.keywords
#                 }
#     logger.info(f'Count of images with differing description in db and exif tags: {len(different_descriptions)}')
#     logger.info(f'Count of images with differing record date in db and exif tags: {len(different_record_dates)}')
#     logger.info(f'Count of images with differing record plants in db and exif tags: {len(different_plants)}')
#     logger.info(f'Count of images with differing record keywords in db and exif tags: {len(different_keywords)}')
#
#     results = {
#         'different_plants': different_plants,
#         'different_keywords': different_keywords,
#         'different_descriptions': different_descriptions,
#         'different_record_dates': different_record_dates,
#         'missing_in_files': missing_in_files,
#         'missing_in_db': missing_in_db,
#         }
#
#     make_dict_values_json_serializable(results)
#
#     return results
#
#
# if __name__ == '__main__':
#     # takes a long time (timeout in browser)
#     comparison = compare_images_in_db_with_exif_tags(next(get_db()))
#     json_string = json.dumps(comparison)
#     with open('/common/_temp_comparison_results_db_exif.json', 'w') as outfile:
#         outfile.write(json_string)
