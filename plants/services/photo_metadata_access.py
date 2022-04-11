from collections import namedtuple
from pathlib import Path
from typing import Protocol
import logging

logger = logging.getLogger(__name__)

MetadataDTO = namedtuple("Metadata_DTO", "plants, keywords, description, record_date_time")


class PhotoMetadataAccess(Protocol):
    def read_photo_metadata(self, absolute_path: Path) -> MetadataDTO:
        """retrieve metadata on photo"""
        raise NotImplementedError

    def save_photo_metadata(self, absolute_path: Path, metadata: MetadataDTO) -> None:
        """save/update photo metadata"""
        raise NotImplementedError

    def rewrite_plant_assignments(self, absolute_path: Path, plants: list[str]) -> None:
        """rewrite the plants assigned to the photo at the supplied path"""
        raise NotImplementedError
