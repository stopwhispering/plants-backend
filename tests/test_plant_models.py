from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from plants.modules.plant.models import Plant

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from plants.modules.plant.plant_dal import PlantDAL


@pytest_asyncio.fixture(scope="function")
async def dummy() -> None:
    """For whatever reason, the unit tests fail with some database connection closed resource error
    if they don't use any function-scoped fixtures."""


@pytest.mark.usefixtures("dummy")
@pytest.mark.asyncio()
async def test_plant_invalid(test_db: AsyncSession) -> None:
    plant = Plant(field_number="A100")  # plant_name, active, deleted are required
    test_db.add(plant)
    with pytest.raises(IntegrityError):
        await test_db.commit()
    await test_db.rollback()

    query = select(Plant).where(Plant.field_number == "A100")
    plants = (await test_db.scalars(query)).all()
    assert len(plants) == 0


@pytest.mark.usefixtures("dummy")
@pytest.mark.asyncio()
async def test_plant_valid(plant_dal: PlantDAL) -> None:
    plant_name = "Aloe Vera"
    plant = Plant(plant_name=plant_name, active=True, deleted=False)
    await plant_dal.save_plant(plant)

    p = await plant_dal.by_name(plant_name)
    assert p is not None
    assert p.plant_name == plant_name
    assert p.id is not None


@pytest.mark.usefixtures("dummy")
@pytest.mark.asyncio()
async def test_plant_duplicate_name(test_db: AsyncSession) -> None:
    test_db.add(Plant(plant_name="Aloe Vera", active=True, deleted=False))
    await test_db.flush()

    test_db.add(Plant(plant_name="Aloe Vera", active=True, deleted=False))
    with pytest.raises(IntegrityError):
        await test_db.commit()
    await test_db.rollback()
