from datetime import datetime

from plants.modules.plant.history_dal import HistoryDAL
from plants.modules.plant.plant_dal import PlantDAL
from plants.shared.history_models import History


def create_history_entry(description: str,
                         history_dal: HistoryDAL,
                         plant_dal: PlantDAL,
                         plant_id: int = None,
                         plant_name: str = None) -> None:
    if plant_id and not plant_name:
        plant_name = plant_dal.get_name_by_id(plant_id)
    elif plant_name and not plant_id:
        plant_id = plant_dal.get_id_by_name(plant_name)

    entry = History(timestamp=datetime.utcnow(),
                    plant_id=plant_id,
                    plant_name=plant_name,
                    description=description)

    history_dal.create(entry)
