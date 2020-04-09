def get_fake_headers():
    # returns headers with fake user agent for requests
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                 'Chrome/35.0.1916.47 Safari/537.36 '
    headers = {'User-Agent': user_agent}
    return headers


def with_suffix(path: str, suffix: str) -> str:
    """return filename or path with a suffix added"""
    path_list = path.split('.')
    if len(path_list) >= 2:
        path_list[-2] = f'{path_list[-2]}{suffix}'
    return ".".join(path_list)
