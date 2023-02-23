from enum import Enum


class TagState(str, Enum):
    NONE = "None"
    INDICATION01 = "Indication01"
    SUCCESS = "Success"
    INFORMATION = "Information"
    ERROR = "Error"
    WARNING = "Warning"


class FBPropagationType(str, Enum):
    SEED_COLLECTED = "seed (collected)"
    OFFSET = "offset"
    ACQUIRED_AS_PLANT = "acquired as plant"
    BULBIL = "bulbil"
    HEAD_CUTTING = "head cutting"
    LEAF_CUTTING = "leaf cutting"
    SEED_PURCHASED = "seed (purchased)"
    UNKNOWN = "unknown"
    NONE = ""


class FBCancellationReason(str, Enum):
    WINTER_DAMAGE = "Winter Damage"
    DRIEDOUT = "Dried Out"
    MOULD = "Mould"
    MITES = "Mites"
    OTHER_INSECTS = "Other Insects"
    ABANDONMENT = "Abandonment"
    GIFT = "Gift"
    SALE = "Sale"
    OTHERS = "Others"
    # NONE = ''
