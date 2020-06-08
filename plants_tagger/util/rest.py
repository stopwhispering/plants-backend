from sqlalchemy import inspect


def object_as_dict(obj):
    # converts an orm object into a dict
    # does not include objects from relationships and _sa_instance_state
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}


def objects_list_to_dict(obj_list) -> dict:
    # converts a list of orm objects into a dict mapping id to dict
    # does not include objects from relationships and _sa_instance_state
    dict_main = {}
    for obj in obj_list:
        dict_sub = {c.key: getattr(obj, c.key)
                    for c in inspect(obj).mapper.column_attrs}
        # get primary key tuple; if only one element, set that as dict key, otherwise the tuple
        primary_key_tuple = inspect(obj).mapper.primary_key_from_instance(obj)
        primary_key = primary_key_tuple[0] if len(primary_key_tuple) == 1 else primary_key_tuple
        dict_main[primary_key] = dict_sub

    return dict_main


def get_fake_headers():
    # returns headers with fake user agent for requests
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                 'Chrome/35.0.1916.47 Safari/537.36 '
    headers = {'User-Agent': user_agent}
    return headers