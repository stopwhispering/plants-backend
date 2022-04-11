from typing import Protocol
import logging

from plants.services.Photo import Photo

logger = logging.getLogger(__name__)


class PhotoFileAccess(Protocol):
    def query_photos(self) -> list[Photo]:
        raise NotImplementedError

    def get_generated_files(self) -> list[str]:
        raise NotImplementedError
