class Error(Exception):
    """Base class for other exceptions"""
    pass


class TooManyResultsError(Error):
    """Raised when database query returned too many results"""
    pass
