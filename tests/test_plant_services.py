import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from plants.modules.plant.event_dal import EventDAL
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.plant.property_dal import PropertyDAL
from plants.modules.plant.services import deep_clone_plant


@pytest.mark.asyncio
async def test_deep_clone_plant(db: AsyncSession,
                                plant_valid,
                                plant_dal: PlantDAL,
                                event_dal: EventDAL,
                                property_dal: PropertyDAL):
    db.add(plant_valid)
    await db.commit()
    plant_valid = await plant_dal.by_id(plant_valid.id)
    # await db.refresh(plant_valid)

    await deep_clone_plant(plant_valid,
                           plant_name_clone='Aloe Vera Clone',
                           plant_dal=plant_dal,
                           event_dal=event_dal,
                           property_dal=property_dal)
    await db.commit()

    cloned_plant = await plant_dal.by_name('Aloe Vera Clone')
    # cloned_plant = Plant.by_name('Aloe Vera Clone', db=db)
    assert cloned_plant is not None
    assert cloned_plant.plant_name == 'Aloe Vera Clone'
    assert cloned_plant.id >= 0 and cloned_plant.id != plant_valid.id
    assert cloned_plant.nursery_source == plant_valid.nursery_source
    assert cloned_plant.field_number == plant_valid.field_number
    assert cloned_plant.propagation_type == plant_valid.propagation_type

    assert cloned_plant.tags != plant_valid.tags
    assert len(cloned_plant.tags) == len(plant_valid.tags)
    assert all([pt.text == ct.text for pt, ct in zip(plant_valid.tags, cloned_plant.tags)])
    assert all(pt.plant_id == cloned_plant.id for pt in cloned_plant.tags)

    assert cloned_plant.filename_previewimage is None
