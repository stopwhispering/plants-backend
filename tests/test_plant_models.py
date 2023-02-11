import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL


@pytest_asyncio.fixture(scope="function")
async def dummy() -> None:
    """for whatever reason, the unit tests fail with some database connection closed resource error if they
    don't use any function-scoped fixtures"""
    pass


@pytest.mark.asyncio
async def test_plant_invalid(db: AsyncSession, plant_dal: PlantDAL, dummy):  # noqa
    plant = Plant(field_number='A100')  # plant_name, active, deleted are required
    db.add(plant)
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()

    plants = await plant_dal.get_plant_by_criteria({'field_number': 'A100'})
    assert len(plants) == 0


@pytest.mark.asyncio
async def test_plant_valid(plant_dal: PlantDAL, dummy):  # noqa
    plant_name = 'Aloe Vera'
    plant = Plant(plant_name=plant_name, active=True, deleted=False)
    await plant_dal.create_plant(plant)

    p = await plant_dal.by_name(plant_name)
    assert p.plant_name == plant_name
    assert p.id is not None


@pytest.mark.asyncio
async def test_plant_duplicate_name(db, dummy):  # noqa
    db.add(Plant(plant_name='Aloe Vera', active=True, deleted=False))
    await db.flush()

    db.add(Plant(plant_name='Aloe Vera', active=True, deleted=False))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()
