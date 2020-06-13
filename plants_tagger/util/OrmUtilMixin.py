from sqlalchemy import inspect


class OrmUtil(object):
    """use as mixin in sqlalchemy models to get database row's fields as dictionary; does NOT consider
    virtual fields (relationships) or @properties"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def as_dict(self):
        """converts an orm object into a dict"""
        # as_dict = self.__dict__.copy()
        # if '_sa_instance_state' in as_dict:
        #     del as_dict['_sa_instance_state']

        # does not include objects from relationships nor _sa_instance_state
        as_dict = {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
        return as_dict
