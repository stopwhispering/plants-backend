from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from plants.modules.pollination.enums import (
    Context,
    FlorescenceStatus,
    FlowerColorDifferentiation,
    StigmaPosition,
)
from plants.modules.pollination.models import Florescence


@pytest.mark.asyncio()
async def test_florescence_flower_attrs(test_db, plant_valid):
    test_db.add(plant_valid)
    await test_db.commit()

    new_florescence = Florescence(
        plant_id=plant_valid.id,
        flowers_count=10,
        perianth_length=Decimal(1.9),
        perianth_diameter=Decimal(0.8),
        flower_color="#f2f600",
        flower_color_second="#ffdd00",
        flower_colors_differentiation=FlowerColorDifferentiation.OVARY_MOUTH,
        stigma_position=StigmaPosition.DEEPLY_INSERTED,
        florescence_status=FlorescenceStatus.FLOWERING,
        creation_context=Context.MANUAL,
    )
    test_db.add(new_florescence)
    await test_db.commit()

    new_florescence = Florescence(
        plant_id=plant_valid.id,
        flowers_count=10,
        perianth_length=Decimal(1.9),
        perianth_diameter=Decimal(0.8),
        flower_color="#f2f600",
        flower_color_second="#ffdd00",
        flower_colors_differentiation=FlowerColorDifferentiation.TOP_BOTTOM,
        stigma_position=StigmaPosition.DEEPLY_INSERTED,
        florescence_status=FlorescenceStatus.FLOWERING,
        # creation_context=Context.API  # required
    )
    test_db.add(new_florescence)
    with pytest.raises(IntegrityError):
        await test_db.commit()
    await test_db.rollback()
