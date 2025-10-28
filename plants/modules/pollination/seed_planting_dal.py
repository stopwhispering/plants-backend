from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from plants.exceptions import SeedPlantingNotFoundError
from plants.modules.pollination.models import Pollination, SeedPlanting
from plants.shared.base_dal import BaseDAL

if TYPE_CHECKING:
    from collections.abc import Collection

    from plants.modules.pollination.enums import SeedPlantingStatus


class SeedPlantingDAL(BaseDAL):
    async def get_plantings(self):
        query = (
            select(SeedPlanting)
            .options(
                selectinload(SeedPlanting.pollination).selectinload(Pollination.seed_capsule_plant)
            )
            .options(
                selectinload(SeedPlanting.pollination).selectinload(Pollination.pollen_donor_plant)
            )
            .options(selectinload(SeedPlanting.soil))
        )
        return list((await self.session.scalars(query)).all())

    async def by_id(self, seed_planting_id: int) -> SeedPlanting:
        # noinspection PyTypeChecker
        query = (
            select(SeedPlanting)
            .where(SeedPlanting.id == seed_planting_id)
            .options(
                selectinload(SeedPlanting.pollination).selectinload(Pollination.seed_capsule_plant)
            )
            .options(
                selectinload(SeedPlanting.pollination).selectinload(Pollination.pollen_donor_plant)
            )
            .options(selectinload(SeedPlanting.soil))
        )
        seed_planting: SeedPlanting | None = (await self.session.scalars(query)).first()
        if not seed_planting:
            raise SeedPlantingNotFoundError(seed_planting_id)
        return seed_planting

    async def by_status(self, status: Collection[SeedPlantingStatus]) -> list[SeedPlanting]:
        query = (
            select(SeedPlanting)
            .where(SeedPlanting.status.in_(status))
            .options(selectinload(SeedPlanting.soil))
            .options(
                selectinload(SeedPlanting.pollination).selectinload(Pollination.seed_capsule_plant)
            )
            .options(
                selectinload(SeedPlanting.pollination).selectinload(Pollination.pollen_donor_plant)
            )
        )
        return list((await self.session.scalars(query)).all())

    async def create(self, seed_planting: SeedPlanting) -> None:
        self.session.add(seed_planting)
        await self.session.flush()

    async def update(  # noqa: C901
        self, seed_planting: SeedPlanting, updates: dict[str, Any]
    ) -> None:
        if "status" in updates:
            seed_planting.status = updates["status"]
        if "pollination_id" in updates:
            seed_planting.pollination_id = updates["pollination_id"]
        if "comment" in updates:
            seed_planting.comment = updates["comment"]
        if "sterilized" in updates:
            seed_planting.sterilized = updates["sterilized"]
        if "soaked" in updates:
            seed_planting.soaked = updates["soaked"]
        if "covered" in updates:
            seed_planting.covered = updates["covered"]
        if "planted_on" in updates:
            seed_planting.planted_on = updates["planted_on"]
        if "abandoned_on" in updates:
            seed_planting.abandoned_on = updates["abandoned_on"]
        if "germinated_first_on" in updates:
            seed_planting.germinated_first_on = updates["germinated_first_on"]
        if "count_planted" in updates:
            seed_planting.count_planted = updates["count_planted"]
        if "count_germinated" in updates:
            seed_planting.count_germinated = updates["count_germinated"]
        if "soil_id" in updates:
            seed_planting.soil_id = updates["soil_id"]

        await self.session.flush()

    async def delete(self, seed_planting: SeedPlanting) -> None:
        await self.session.delete(seed_planting)
        await self.session.flush()
