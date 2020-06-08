def with_suffix(path: str, suffix: str) -> str:
    """return filename or path with a suffix added"""
    path_list = path.split('.')
    if len(path_list) >= 2:
        path_list[-2] = f'{path_list[-2]}{suffix}'
    return ".".join(path_list)