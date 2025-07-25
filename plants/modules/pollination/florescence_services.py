"""Services for florescence and pollination-related operations; mostly for pollination frontend."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from plants.exceptions import BaseError, FlorescenceWithoutTaxonError
from plants.modules.pollination.enums import (
    Context,
    FlorescenceStatus,
    FlowerColorDifferentiation,
)
from plants.modules.pollination.models import Florescence
from plants.modules.pollination.schemas import (
    BPlantForNewFlorescence,
    FlorescenceCreate,
    FlorescenceRead,
    FlorescenceUpdate,
)
from plants.shared.api_utils import format_api_date, parse_api_date

if TYPE_CHECKING:
    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.pollination.florescence_dal import FlorescenceDAL
    from plants.modules.pollination.pollination_dal import PollinationDAL


async def read_plants_for_new_florescence(
    plant_dal: PlantDAL,
) -> list[BPlantForNewFlorescence]:
    """Read all plants with genus for the new florescence dialog."""
    plants: list[Plant] = await plant_dal.get_all_plants_with_taxon()

    plants_for_new_florescence = []
    for plant in plants:
        plants_for_new_florescence.append(
            BPlantForNewFlorescence(
                plant_id=plant.id,
                plant_name=plant.plant_name,
                genus=plant.taxon.genus if plant.taxon else None,
            )
        )
    return plants_for_new_florescence


async def read_active_florescences(
    florescence_dal: FlorescenceDAL,
    pollination_dal: PollinationDAL,
) -> list[FlorescenceRead]:
    """Read all active florescences for the pollination frontend main table."""
    florescences_orm = await florescence_dal.by_status(
        {FlorescenceStatus.FLOWERING, FlorescenceStatus.INFLORESCENCE_APPEARED}
    )
    florescences = []
    flor: Florescence
    for flor in florescences_orm:
        # noinspection PyTypeChecker
        f_dict = {
            "id": flor.id,
            "plant_id": flor.plant_id,
            "plant_name": flor.plant.plant_name if flor.plant else None,
            "plant_taxon_name": flor.plant.taxon.name if flor.plant and flor.plant.taxon else None,
            "self_pollinated": flor.self_pollinated,
            "plant_self_pollinates": flor.plant.self_pollinates if flor.plant else None,
            "plant_preview_image_id": flor.plant.preview_image_id,
            "florescence_status": flor.florescence_status,
            "inflorescence_appeared_at": format_api_date(flor.inflorescence_appeared_at),
            "comment": flor.comment,
            "branches_count": flor.branches_count,
            "flowers_count": flor.flowers_count,
            "perianth_length": flor.perianth_length,
            "perianth_diameter": flor.perianth_diameter,
            "flower_color": flor.flower_color,
            "flower_color_second": flor.flower_color_second,
            "flower_colors_differentiation": flor.flower_colors_differentiation,
            "stigma_position": flor.stigma_position,
            "first_flower_opened_at": format_api_date(flor.first_flower_opened_at),
            "last_flower_closed_at": format_api_date(flor.last_flower_closed_at),
            "available_colors_rgb": (
                await pollination_dal.get_available_colors_for_florescence(florescence=flor)
            ),
        }
        # florescences.append(FlorescenceRead.parse_obj(f_dict))
        florescences.append(FlorescenceRead.model_validate(f_dict))

    return florescences


async def update_active_florescence(
    florescence: Florescence,
    edited_florescence_data: FlorescenceUpdate,
    florescence_dal: FlorescenceDAL,
) -> None:
    """Update db record of a currently active florescence."""
    # technical validation
    if florescence.plant_id != edited_florescence_data.plant_id:
        raise HTTPException(
            status_code=400,
            detail="Different plant_id in florescence and edited_florescence_data",
        )

    if (
        edited_florescence_data.flower_colors_differentiation
        in {
            FlowerColorDifferentiation.TOP_BOTTOM,
            FlowerColorDifferentiation.OVARY_MOUTH,
        }
        and not edited_florescence_data.flower_color_second
    ):
        raise HTTPException(
            status_code=400,
            detail="flower_color_second is required " "if flower_colors_differentiation is set",
        )

    if (
        edited_florescence_data.flower_colors_differentiation == FlowerColorDifferentiation.UNIFORM
        and edited_florescence_data.flower_color_second
    ):
        raise HTTPException(
            status_code=400,
            detail="Supplied two colors but UNIFORM differentiation is set",
        )

    if (
        edited_florescence_data.flower_color
        and edited_florescence_data.flower_color_second == edited_florescence_data.flower_color
    ):
        raise HTTPException(
            status_code=400,
            detail="flower_color_second must be different from flower_color",
        )

    # updates = edited_florescence_data.dict(exclude={})
    updates = edited_florescence_data.model_dump(exclude={})
    updates["first_flower_opened_at"] = parse_api_date(
        edited_florescence_data.first_flower_opened_at
    )
    updates["last_flower_closed_at"] = parse_api_date(edited_florescence_data.last_flower_closed_at)
    updates["inflorescence_appeared_at"] = parse_api_date(
        edited_florescence_data.inflorescence_appeared_at
    )
    updates["last_update_context"] = Context.API

    await florescence_dal.update_florescence(florescence, updates=updates)

    # if edited_florescence_data.plant_self_pollinates is not florescence.plant.self_pollinates:
    #     await plant_dal.set_self_pollinates(
    #         plant=florescence.plant,
    #         self_pollinates=edited_florescence_data.plant_self_pollinates)


async def create_new_florescence(
    new_florescence_data: FlorescenceCreate,
    florescence_dal: FlorescenceDAL,
    plant_dal: PlantDAL,
) -> None:
    """Create a new active florescence."""
    plant = await plant_dal.by_id(new_florescence_data.plant_id)

    if not plant.taxon:
        raise FlorescenceWithoutTaxonError(
            plant_id=new_florescence_data.plant_id, plant_name=plant.plant_name
        )

    florescence = Florescence(
        plant_id=new_florescence_data.plant_id,
        plant=plant,
        florescence_status=new_florescence_data.florescence_status,
        inflorescence_appeared_at=parse_api_date(new_florescence_data.inflorescence_appeared_at),
        first_flower_opened_at=parse_api_date(new_florescence_data.first_flower_opened_at),
        comment=new_florescence_data.comment,
        creation_context=Context.API,
    )
    await florescence_dal.create_florescence(florescence)


async def remove_florescence(florescence: Florescence, florescence_dal: FlorescenceDAL) -> None:
    """Delete a florescence."""
    if florescence.pollinations:
        raise BaseError(detail={"message": "Florescence has pollinations"})
    await florescence_dal.delete_florescence(florescence)
