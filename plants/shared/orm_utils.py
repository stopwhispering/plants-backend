from sqlalchemy import inspect


def get_fake_headers():
    # returns headers with fake user agent for requests
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                 'Chrome/35.0.1916.47 Safari/537.36 '
    headers = {'User-Agent': user_agent}
    return headers


class OrmAsDict(object):
    # todo replace with pydantic's from_orm
    """use as mixin in sqlalchemy models to get database row's fields as dictionary; does NOT consider
    virtual fields (relationships) or @properties"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def as_dict(self):
        """converts an orm object into a dict"""
        # does not include objects from relationships nor _sa_instance_state
        as_dict = {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
        return as_dict
