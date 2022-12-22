from enum import Enum


class Scale(Enum):
    NOMINAL = 'nominal'
    ORDINAL = 'ordinal'
    METRIC = 'metric'
    NOMINAL_BIVALUE = 'nominal_bivalue'  # e.g. 'fresh' / 'frozen'
    BOOLEAN = 'boolean'  # True / False, requires no one-hot-encoding


class DBType(Enum):
    POSTGRES = 'postgres'
    SQLITE = 'sqlite'
    UNKNOWN = 'unknown'


class Feature:
    def __init__(self, scale: Scale, column: str):
        self.column = column
        self.scale = scale


class FeatureContainer:
    def __init__(self, features: list[Feature]):
        self.features = features

    def get_columns(self, scale: Scale = None) -> list[str]:
        """return - distinct - column names, optionally filtered by scale type"""
        if scale:
            # columns = [c for f in self.features if f.scale == scale for c in f.column]
            columns = [f.column for f in self.features if f.scale == scale]
        else:
            # columns = [c for f in self.features for c in f.column]
            columns = [f.column for f in self.features]
        return list(dict.fromkeys(columns))
