from sqlalchemy import select

from plants.shared.base_dal import BaseDAL
from plants.shared.history_models import History


class HistoryDAL(BaseDAL):
    def __init__(self, session):
        super().__init__(session)

    def create(self, history: History):
        self.session.add(history)
        self.session.flush()
