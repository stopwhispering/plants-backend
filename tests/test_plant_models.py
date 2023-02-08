import pytest
from sqlalchemy.exc import IntegrityError

from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL


@pytest.mark.asyncio
async def test_plant_invalid(db, plant_dal: PlantDAL):
    plant = Plant(field_number='A100')
    db.add(plant)
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()

    plants = await plant_dal.get_plant_by_criteria({'field_number': 'A100'})
    assert len(plants) == 0


@pytest.mark.asyncio
async def test_plant_valid(db, plant_dal: PlantDAL):
    plant_name = 'Aloe Vera'
    plant = Plant(plant_name=plant_name, active=True, deleted=False)
    db.add(plant)
    await db.commit()

    p = await plant_dal.by_name(plant_name)
    assert p.plant_name == plant_name
    assert p.id is not None


@pytest.mark.asyncio
async def test_plant_duplicate_name(db):
    db.add(Plant(plant_name='Aloe Vera', active=True, deleted=False))
    await db.commit()

    db.add(Plant(plant_name='Aloe Vera', active=True, deleted=False))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()
