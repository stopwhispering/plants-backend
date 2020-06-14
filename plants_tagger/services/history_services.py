from datetime import datetime

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.history_model import History
from plants_tagger.models.plant_models import Plant


def create_history_entry(description: str, plant_id: int = None, plant_name: str = None, commit: bool = True):
    if plant_id and not plant_name:
        plant_name = get_sql_session().query(Plant.plant_name).filter(Plant.id == plant_id).scalar()
    elif plant_name and not plant_id:
        plant_id = get_sql_session().query(Plant.id).filter(Plant.plant_name == plant_name).scalar()

    entry = History(timestamp=datetime.now(),
                    plant_id=plant_id,
                    plant_name=plant_name,
                    description=description)

    get_sql_session().add(entry)
    if commit:
        get_sql_session().commit()
