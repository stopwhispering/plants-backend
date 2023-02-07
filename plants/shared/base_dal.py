from sqlalchemy.orm import Session


class BaseDAL(object):
    def __init__(self, session: Session ):
        self.session = session
