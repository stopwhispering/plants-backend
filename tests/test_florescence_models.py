from decimal import Decimal

import pytest
from sqlalchemy.exc import DataError, IntegrityError

from plants.modules.pollination.models import Florescence, StigmaPosition, FlowerColorDifferentiation, Context, \
    BFlorescenceStatus


def test_florescence_flower_attrs(db, plant_valid):
    print('wtf debugger')
    db.add(plant_valid)
    db.commit()

    new_florescence = Florescence(
        plant_id=plant_valid.id,
        flowers_count=10,
        perianth_length=Decimal(1.9),
        perianth_diameter=Decimal(0.8),
        flower_color="#f2f600",
        flower_color_second = "#ffdd00",
        flower_colors_differentiation = FlowerColorDifferentiation.OVARY_MOUTH,
        stigma_position=StigmaPosition.DEEPLY_INSERTED,
        florescence_status=BFlorescenceStatus.FLOWERING,
        creation_context=Context.MANUAL)
    db.add(new_florescence)
    db.commit()

    new_florescence = Florescence(
        plant_id=plant_valid.id,
        flowers_count=10,
        perianth_length=Decimal(1.9),
        perianth_diameter=Decimal(0.8),
        flower_color="#f2f600",
        flower_color_second = "#ffdd00",
        flower_colors_differentiation = FlowerColorDifferentiation.TOP_BOTTOM,
        stigma_position=StigmaPosition.DEEPLY_INSERTED,
        florescence_status=BFlorescenceStatus.FLOWERING,
        # creation_context=Context.API  # required
    )
    db.add(new_florescence)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
