def is_number(s: str) -> bool:
    """str.isnumeric() returns False for floats, so we make up our own number checker"""
    try:
        float(s)
        return True
    except ValueError:
        return False
