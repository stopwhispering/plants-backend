from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from plants.exceptions import CriterionNotImplementedError, PollinationNotFoundError
from plants.modules.pollination.enums import COLORS_MAP_TO_RGB, PollinationStatus
from plants.modules.pollination.models import Florescence, Pollination, SeedPlanting
from plants.shared.base_dal import BaseDAL

if TYPE_CHECKING:
    from plants.modules.plant.models import Plant


class PollinationDAL(BaseDAL):
    async def by_id(self, pollination_id: int) -> Pollination:
        # noinspection PyTypeChecker
        query = select(Pollination).where(Pollination.id == pollination_id)
        query = query.options(selectinload(Pollination.seed_plantings))
        pollination: Pollination | None = (await self.session.scalars(query)).first()
        if not pollination:
            raise PollinationNotFoundError(pollination_id)
        return pollination

    async def create(self, pollination: Pollination) -> None:
        self.session.add(pollination)
        await self.session.flush()

    async def delete(self, pollination: Pollination) -> None:
        await self.session.delete(pollination)
        await self.session.flush()

    async def update(  # noqa: C901 PLR0912
        self, pollination: Pollination, updates: dict[str, Any]
    ) -> None:
        if "pollen_type" in updates:
            pollination.pollen_type = updates["pollen_type"]
        if "location" in updates:
            pollination.location = updates["location"]
        if "pollinated_at" in updates:
            pollination.pollinated_at = updates["pollinated_at"]
        if "count_attempted" in updates:
            pollination.count_attempted = updates["count_attempted"]
        if "count_pollinated" in updates:
            pollination.count_pollinated = updates["count_pollinated"]
        if "count_capsules" in updates:
            pollination.count_capsules = updates["count_capsules"]
        if "label_color" in updates:
            pollination.label_color = updates["label_color"]
        if "pollination_status" in updates:
            pollination.pollination_status = updates["pollination_status"]
        if "ongoing" in updates:
            pollination.ongoing = updates["ongoing"]
        if "harvest_date" in updates:
            pollination.harvest_date = updates["harvest_date"]
        if "seed_capsule_length" in updates:
            pollination.seed_capsule_length = updates["seed_capsule_length"]
        if "seed_capsule_width" in updates:
            pollination.seed_capsule_width = updates["seed_capsule_width"]
        if "seed_length" in updates:
            pollination.seed_length = updates["seed_length"]
        if "seed_width" in updates:
            pollination.seed_width = updates["seed_width"]
        if "seed_count" in updates:
            pollination.seed_count = updates["seed_count"]
        if "seed_capsule_description" in updates:
            pollination.seed_capsule_description = updates["seed_capsule_description"]
        if "seed_description" in updates:
            pollination.seed_description = updates["seed_description"]
        if "last_update_context" in updates:
            pollination.last_update_context = updates["last_update_context"]

        await self.session.flush()

    async def get_ongoing_pollinations(self) -> list[Pollination]:
        # noinspection PyTypeChecker
        query = (
            select(Pollination)
            .where(Pollination.ongoing)
            .options(
                selectinload(Pollination.seed_capsule_plant),
                selectinload(Pollination.pollen_donor_plant),
                selectinload(Pollination.seed_plantings)
                .selectinload(SeedPlanting.pollination)
                .selectinload(Pollination.seed_capsule_plant),
                selectinload(Pollination.seed_plantings)
                .selectinload(SeedPlanting.pollination)
                .selectinload(Pollination.pollen_donor_plant),
                selectinload(Pollination.seed_plantings).selectinload(SeedPlanting.plants),
                selectinload(Pollination.seed_plantings).selectinload(SeedPlanting.soil),
                selectinload(Pollination.florescence),
            )
        )
        pollinations: list[Pollination] = list((await self.session.scalars(query)).all())
        return pollinations

    async def get_available_colors_for_florescence(self, florescence: Florescence) -> list[str]:
        # noinspection PyTypeChecker
        used_colors_query = select(Pollination.label_color).where(
            # Pollination.seed_capsule_plant_id == plant.id,
            Pollination.florescence_id == florescence.id,
            Pollination.ongoing,
        )
        used_colors = (await self.session.scalars(used_colors_query)).all()
        available_color_names = [c for c in COLORS_MAP_TO_RGB if c not in used_colors]
        return [COLORS_MAP_TO_RGB[c] for c in available_color_names]

    async def get_pollinations_with_filter(self, criteria: dict[str, Any]) -> list[Pollination]:
        query = select(Pollination)

        for key, value in criteria.items():
            if key == "ongoing":
                query = query.where(Pollination.ongoing == value)
            elif key == "seed_capsule_plant":
                query = query.where(Pollination.seed_capsule_plant == value)
            elif key == "pollen_donor_plant":
                query = query.where(Pollination.pollen_donor_plant == value)
            elif key == "seed_capsule_plant_id":
                query = query.where(Pollination.seed_capsule_plant_id == value)
            elif key == "label_color":
                query = query.where(Pollination.label_color == value)
            elif key == "florescence_id":
                query = query.where(Pollination.florescence_id == value)
            else:
                raise CriterionNotImplementedError(key)

        pollinations: list[Pollination] = list((await self.session.scalars(query)).all())
        return pollinations

    async def get_pollinations_by_plants(
        self, seed_capsule_plant: Plant, pollen_donor_plant: Plant
    ) -> list[Pollination]:
        # noinspection PyTypeChecker
        query = select(Pollination).where(
            Pollination.seed_capsule_plant_id == seed_capsule_plant.id,
            Pollination.pollen_donor_plant_id == pollen_donor_plant.id,
        )

        pollinations: list[Pollination] = list((await self.session.scalars(query)).all())
        return pollinations

    async def get_pollinations_by_plant_ids(
        self, seed_capsule_plant_id: int, pollen_donor_plant_id: int
    ) -> list[Pollination]:
        # noinspection PyTypeChecker
        query = select(Pollination).where(
            Pollination.seed_capsule_plant_id == seed_capsule_plant_id,
            Pollination.pollen_donor_plant_id == pollen_donor_plant_id,
        )

        pollinations: list[Pollination] = list((await self.session.scalars(query)).all())
        return pollinations

    async def set_status(self, pollination: Pollination, status: PollinationStatus) -> None:
        pollination.pollination_status = status
        await self.session.flush()
