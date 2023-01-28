from typing import Final

PROPERTY_CATEGORIES: Final[list[str]] = ['Plant', 'Leaves', 'Flowers', 'Care', 'Habitat', 'Trivia', 'Taxonomy', 'Others']
RESIZE_SUFFIX: Final[str] = '_autoresized'
REGEX_DATE: Final[str] = r'^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$'  # string yyyy-mm-dd
