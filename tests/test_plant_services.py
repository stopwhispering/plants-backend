from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from plants.modules.plant.services import deep_clone_plant

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from plants.modules.event.event_dal import EventDAL
    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL


@pytest.mark.asyncio()
async def test_deep_clone_plant(
    test_db: AsyncSession,
    plant_valid_in_db: Plant,
    plant_dal: PlantDAL,
    event_dal: EventDAL,
) -> None:
    plant_id = plant_valid_in_db.id

    await deep_clone_plant(
        plant_valid_in_db,
        plant_name_clone="Aloe Vera Clone",
        plant_dal=plant_dal,
        event_dal=event_dal,
        # property_dal=property_dal
    )
    await test_db.commit()

    test_db.expire_all()
    _ = await plant_dal.by_id(plant_id)

    cloned_plant = await plant_dal.by_name("Aloe Vera Clone")
    assert cloned_plant is not None
    assert cloned_plant.plant_name == "Aloe Vera Clone"
    assert cloned_plant.id >= 0
    assert cloned_plant.id != plant_id
    assert cloned_plant.nursery_source == plant_valid_in_db.nursery_source
    assert cloned_plant.field_number == plant_valid_in_db.field_number
    assert cloned_plant.propagation_type == plant_valid_in_db.propagation_type

    assert cloned_plant.tags != plant_valid_in_db.tags
    assert len(cloned_plant.tags) == len(plant_valid_in_db.tags)
    assert all(pt.text == ct.text for pt, ct in zip(plant_valid_in_db.tags, cloned_plant.tags))
    assert all(pt.plant_id == cloned_plant.id for pt in cloned_plant.tags)

    assert cloned_plant.preview_image_id is None
