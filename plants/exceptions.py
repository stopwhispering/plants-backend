from fastapi import HTTPException


class TooManyResultsError(Exception):
    """Raised when database query returned too many results"""
    pass


class BaseError(HTTPException):
    """Base class for exceptions raised by this application"""

    def __init__(self, detail: str | dict):
        super().__init__(status_code=404, detail=detail)


class PlantNotFound(BaseError):
    """Raised when plant not found in database"""

    def __init__(self, plant_identifier: int | str):
        msg = (f"Plant ID not found in database: {plant_identifier}" if isinstance(plant_identifier, int)
               else f"Plant Name not found in database: {plant_identifier}")
        super().__init__(detail=msg)


class PollinationNotFound(BaseError):
    """Raised when pollination not found in database"""

    def __init__(self, pollination_id: int):
        super().__init__(detail=f"Pollination ID not found in database: {pollination_id}")


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
