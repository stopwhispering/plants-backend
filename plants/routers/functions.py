from fastapi import APIRouter
import logging
from starlette.requests import Request

from plants.util.ui_utils import get_message
from plants.validation.message_validation import PConfirmation
from plants.services.PhotoDirectory import lock_photo_directory, get_photo_directory

logger = logging.getLogger(__name__)

router = APIRouter(
        tags=["functions"],
        responses={404: {"description": "Not found"}},
        )


@router.post("/functions/refresh_photo_directory", response_model=PConfirmation)
async def refresh_photo_directory(request: Request):
    """recreates the photo directory, i.e. re-reads directory, creates missing thumbnails etc."""
    with lock_photo_directory:
        get_photo_directory().refresh_directory()

    logger.info(message := f'Refreshed photo directory')
    results = {'action':   'Function refresh Photo Directory',
               'resource': 'RefreshPhotoDirectoryResource',
               'message':  get_message(message)}

    return results
