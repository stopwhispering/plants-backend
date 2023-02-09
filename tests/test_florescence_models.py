from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from plants.modules.pollination.models import (Florescence)
from plants.modules.pollination.enums import Context, FlorescenceStatus, FlowerColorDifferentiation, StigmaPosition


@pytest.mark.asyncio
async def test_florescence_flower_attrs(db, plant_valid):
    db.add(plant_valid)
    await db.commit()

    new_florescence = Florescence(
        plant_id=plant_valid.id,
        flowers_count=10,
        perianth_length=Decimal(1.9),
        perianth_diameter=Decimal(0.8),
        flower_color="#f2f600",
        flower_color_second = "#ffdd00",
        flower_colors_differentiation = FlowerColorDifferentiation.OVARY_MOUTH,
        stigma_position=StigmaPosition.DEEPLY_INSERTED,
        florescence_status=FlorescenceStatus.FLOWERING,
        creation_context=Context.MANUAL)
    db.add(new_florescence)
    await db.commit()

    new_florescence = Florescence(
        plant_id=plant_valid.id,
        flowers_count=10,
        perianth_length=Decimal(1.9),
        perianth_diameter=Decimal(0.8),
        flower_color="#f2f600",
        flower_color_second = "#ffdd00",
        flower_colors_differentiation = FlowerColorDifferentiation.TOP_BOTTOM,
        stigma_position=StigmaPosition.DEEPLY_INSERTED,
        florescence_status=FlorescenceStatus.FLOWERING,
        # creation_context=Context.API  # required
    )
    db.add(new_florescence)
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()
