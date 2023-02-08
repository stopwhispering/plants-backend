from fastapi import HTTPException


class TooManyResultsError(Exception):
    """Raised when database query returned too many results"""
    pass


class BaseError(HTTPException):
    """Base class for exceptions raised by this application"""

    def __init__(self, detail: str | dict):
        super().__init__(status_code=404, detail=detail)


class UnknownColor(BaseError):
    def __init__(self, color: str):
        super().__init__(detail=f"Unknown Color: {color}")


class ColorAlreadyTaken(BaseError):
    def __init__(self, plant_name: str, color: str):
        super().__init__(detail=f"Color {color} already used for current florescence at {plant_name}")


class TaxonAlreadyExists(BaseError):
    """"""

    def __init__(self, taxon_name: str):
        super().__init__(detail=f"Taxon already exists: {taxon_name}")


class PlantAlreadyExists(BaseError):
    """"""

    def __init__(self, plant_name: str):
        super().__init__(detail=f"Plant already exists: {plant_name}")


class DuplicatePlantName(BaseError):
    """Base class for exceptions raised by this application"""

    def __init__(self, plant_name: str):
        super().__init__(detail=f"Duplicate Plant Name: {plant_name}")


class PlantNotFound(BaseError):
    """Raised when plant not found in database"""

    def __init__(self, plant_identifier: int | str):
        msg = (f"Plant ID not found in database: {plant_identifier}" if isinstance(plant_identifier, int)
               else f"Plant Name not found in database: {plant_identifier}")
        super().__init__(detail=msg)


class TagNotAssignedToPlant(BaseError):
    """Raised when tag is unexpectedly not found in tags assigned to a plant"""

    def __init__(self, plant_id: int, tag_id: int):
        super().__init__(detail=f'Tag {tag_id} not assigned to plant {plant_id}')


class ImageNotAssignedToTaxon(BaseError):
    """Raised when Image is unexpectedly not found in images assigned to a taxon"""

    def __init__(self, taxon_id: int, image_id: int):
        super().__init__(detail=f'Taxon {taxon_id} has no association to image {image_id}')


class PollinationNotFound(BaseError):
    """Raised when pollination not found in database"""

    def __init__(self, pollination_id: int):
        super().__init__(detail=f"Pollination ID not found in database: {pollination_id}")


class TagNotFound(BaseError):
    """Raised when tag not found in database"""

    def __init__(self, tag_id: int):
        super().__init__(detail=f"TAG ID not found in database: {tag_id}")


class FlorescenceNotFound(BaseError):
    """Raised when florescence not found in database"""

    def __init__(self, florescence_id: int):
        super().__init__(detail=f"Florescence ID not found in database: {florescence_id}")


class TaxonNotFound(BaseError):
    """Raised when taxon not found in database"""

    def __init__(self, taxon_identifier: int | str):
        msg = (f"Taxon ID not found in database: {taxon_identifier}" if isinstance(taxon_identifier, int)
               else f"Taxon Name not found in database: {taxon_identifier}")
        super().__init__(detail=msg)


class EventNotFound(BaseError):
    """Raised when event, looked for by ID, not found in database"""

    def __init__(self, image_id: int | str):
        super().__init__(detail=f"Event {image_id} not found in database")


class SoilNotFound(BaseError):
    """Raised when soil, looked for by ID, not found in database"""

    def __init__(self, soil_id: int):
        super().__init__(detail=f"Soil {soil_id} not found in database")


class SoilNotUnique(BaseError):
    """Raised when soil to be created with existing name"""

    def __init__(self, soil_name: str):
        super().__init__(detail=f"Soil {soil_name} not unique.")


class ImageNotFound(BaseError):
    """Raised when image, looked for by ID, not found in database"""

    def __init__(self, image_id: int | str):
        super().__init__(detail=f"Image {image_id} not found in database")


class PropertyCategoryNotFound(BaseError):
    """Raised when property category, looked for by ID, not found in database"""

    def __init__(self, property_category_id: int | str):
        super().__init__(detail=f"Property category {str(property_category_id)} not found in database")


class PropertyValueNotFound(BaseError):
    """Raised when property value, looked for by ID, not found in database"""

    def __init__(self, property_value_id: int | str):
        super().__init__(detail=f"Property value {str(property_value_id)} not found in database")
