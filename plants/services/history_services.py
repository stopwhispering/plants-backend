from datetime import datetime
from sqlalchemy.orm import Session

from plants.models.history_model import History
from plants.models.plant_models import Plant


def create_history_entry(description: str,
                         db: Session,
                         plant_id: int = None,
                         plant_name: str = None,
                         commit: bool = True) -> None:
    if plant_id and not plant_name:
        plant_name = db.query(Plant.plant_name).filter(Plant.id == plant_id).scalar()
    elif plant_name and not plant_id:
        plant_id = db.query(Plant.id).filter(Plant.plant_name == plant_name).scalar()

    entry = History(timestamp=datetime.now(),
                    plant_id=plant_id,
                    plant_name=plant_name,
                    description=description)

    db.add(entry)
    if commit:
        db.commit()
