from __future__ import annotations

from fastapi import HTTPException
from starlette import status


class TooManyResultsError(HTTPException):
    """Raised when database query returned too many results."""

    def __init__(self, search_pattern: str, count: int):
        super().__init__(
            status_code=400,
            detail=f"Too many search results for pattern " f"'{search_pattern}' ({count} results)",
        )


class BaseError(HTTPException):
    """Base class for exceptions raised by this application."""

    def __init__(self, detail: str | dict[str, str | None], status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


class ValidationError(BaseError):
    def __init__(self, detail: str):
        super().__init__(detail=detail)


class UnknownColorError(BaseError):
    def __init__(self, color: str | None):
        super().__init__(detail=f"Unknown Color: {color}")


class CriterionNotImplementedError(BaseError):
    def __init__(self, criterion: str):
        super().__init__(
            detail=f"Criterion {criterion} not implemented",
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
        )


class UpdateNotImplementedError(BaseError):
    def __init__(self, attribute: str):
        super().__init__(
            detail=f"Update of attribute {attribute} not implemted",
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
        )


class ColorAlreadyTakenError(BaseError):
    def __init__(self, plant_name: str, color: str):
        super().__init__(
            detail=f"Color {color} already used for current florescence at {plant_name}"
        )


class TaxonAlreadyExistsError(BaseError):
    """"""

    def __init__(self, taxon_name: str):
        super().__init__(detail=f"Taxon already exists: {taxon_name}")


class PlantAlreadyExistsError(BaseError):
    """"""

    def __init__(self, plant_name: str):
        super().__init__(detail=f"Plant already exists: {plant_name}")


class DuplicatePlantNameError(BaseError):
    """Base class for exceptions raised by this application."""

    def __init__(self, plant_name: str):
        super().__init__(detail=f"Duplicate Plant Name: {plant_name}")


class PlantNotFoundError(BaseError):
    """Raised when plant not found in database."""

    def __init__(self, plant_identifier: int | str):
        msg = (
            f"Plant ID not found in database: {plant_identifier}"
            if isinstance(plant_identifier, int)
            else f"Plant Name not found in database: {plant_identifier}"
        )
        super().__init__(detail=msg, status_code=status.HTTP_404_NOT_FOUND)


class TagNotAssignedToPlantError(BaseError):
    """Raised when tag is unexpectedly not found in tags assigned to a plant."""

    def __init__(self, plant_id: int, tag_id: int):
        super().__init__(
            detail=f"Tag {tag_id} not assigned to plant {plant_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class TagNotAssignedToTaxonError(BaseError):
    """Raised when tag is unexpectedly not found in tags assigned to a taxon."""

    def __init__(self, taxon_id: int, tag_id: int):
        super().__init__(
            detail=f"Tag {tag_id} not assigned to taxon {taxon_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ImageNotAssignedToTaxonError(BaseError):
    """Raised when Image is unexpectedly not found in images assigned to a taxon."""

    def __init__(self, taxon_id: int, image_id: int):
        super().__init__(
            detail=f"Taxon {taxon_id} has no association to image {image_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class PollinationNotFoundError(BaseError):
    """Raised when pollination not found in database."""

    def __init__(self, pollination_id: int):
        super().__init__(
            detail=f"Pollination ID not found in database: {pollination_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class SeedPlantingNotFoundError(BaseError):
    """Raised when seed planting not found in database."""

    def __init__(self, seed_planting_id: int):
        super().__init__(
            detail=f"Seed Planting ID not found in database: {seed_planting_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class TagNotFoundError(BaseError):
    """Raised when tag not found in database."""

    def __init__(self, tag_id: int):
        super().__init__(
            detail=f"TAG ID not found in database: {tag_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class FlorescenceNotFoundError(BaseError):
    """Raised when florescence not found in database."""

    def __init__(self, florescence_id: int):
        super().__init__(
            detail=f"Florescence ID not found in database: {florescence_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class TaxonNotFoundError(BaseError):
    """Raised when taxon not found in database."""

    def __init__(self, taxon_identifier: int | str):
        msg = (
            f"Taxon ID not found in database: {taxon_identifier}"
            if isinstance(taxon_identifier, int)
            else f"Taxon Name not found in database: {taxon_identifier}"
        )
        super().__init__(detail=msg, status_code=status.HTTP_404_NOT_FOUND)


class EventNotFoundError(BaseError):
    """Raised when event, looked for by ID, not found in database."""

    def __init__(self, image_id: int | str):
        super().__init__(
            detail=f"Event {image_id} not found in database",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class SoilNotFoundError(BaseError):
    """Raised when soil, looked for by ID, not found in database."""

    def __init__(self, soil_id: int):
        super().__init__(
            detail=f"Soil {soil_id} not found in database",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class SoilNotUniqueError(BaseError):
    """Raised when soil to be created with existing name."""

    def __init__(self, soil_name: str):
        super().__init__(detail=f"Soil {soil_name} not unique.")


class ImageNotFoundError(BaseError):
    """Raised when image, looked for by ID, not found in database."""

    def __init__(self, image_id: int | str):
        super().__init__(
            detail=f"Image {image_id} not found in database",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ImageFileNotFoundError(BaseError):
    """Raised when image, looked for by filename, not found in filesystem."""

    def __init__(self, filename: str):
        super().__init__(
            detail=f"Image file {filename} not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ImageDbRecordExistsError(BaseError):
    def __init__(self, filename: str):
        super().__init__(
            detail=f"Image already exists in db: {filename}.", status_code=status.HTTP_409_CONFLICT
        )


class TrainingError(BaseError):
    def __init__(self, msg: str):
        super().__init__(
            detail=f"Model training failed: {msg}.", status_code=status.HTTP_409_CONFLICT
        )
