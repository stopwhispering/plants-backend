from __future__ import annotations

from enum import Enum


class FProposalEntity(str, Enum):
    """proposal entities that may be requested by frontend"""
    SOIL = 'SoilProposals'
    NURSERY = 'NurserySourceProposals'
    KEYWORD = 'KeywordProposals'


class FBMajorResource(str, Enum):
    PLANT = "PlantResource"
    IMAGE = "ImageResource"
    TAXON = "TaxonResource"
    EVENT = "EventResource"


class BMessageType(str, Enum):
    """message types processed by error/success handlers in ui5 web frontend"""
    INFORMATION = 'Information'
    NONE = 'None'
    SUCCESS = 'Success'
    WARNING = 'Warning'
    ERROR = 'Error'
    DEBUG = 'Debug'  # not known by UI5 message processor, only shown in frontend console log
