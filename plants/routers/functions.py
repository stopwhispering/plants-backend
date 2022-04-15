from fastapi import APIRouter, Depends
import logging

from sqlalchemy.orm import Session

from plants.dependencies import get_db
from plants.deprecated.photo_directory import PhotoFactoryDatabase, PhotoFactoryLocalFiles
from plants.util.ui_utils import make_dict_values_json_serializable

logger = logging.getLogger(__name__)

router = APIRouter(
        tags=["functions"],
        responses={404: {"description": "Not found"}},
        )

# @router.post("/functions/refresh_photo_directory", response_model=PConfirmation)
# async def refresh_photo_directory():
#     """recreates the photo_file directory, i.e. re-reads directory, creates missing thumbnails etc."""
#     with lock_photo_directory:
#         get_photo_directory().refresh_directory()
#
#     logger.info(message := f'Refreshed photo_file directory')
#     results = {'action':   'Function refresh Photo Directory',
#                'resource': 'RefreshPhotoDirectoryResource',
#                'message':  get_message(message)}
#
#     return results
