from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from plants.exceptions import SeedPlantingNotFoundError
from plants.modules.pollination.models import SeedPlanting
from plants.shared.base_dal import BaseDAL

if TYPE_CHECKING:
    from collections.abc import Collection

    from plants.modules.pollination.enums import SeedPlantingStatus


class SeedPlantingDAL(BaseDAL):
    async def by_id(self, seed_planting_id: int) -> SeedPlanting:
        # noinspection PyTypeChecker
        query = select(SeedPlanting).where(SeedPlanting.id == seed_planting_id)
        seed_planting: SeedPlanting | None = (await self.session.scalars(query)).first()
        if not seed_planting:
            raise SeedPlantingNotFoundError(seed_planting_id)
        return seed_planting

    async def by_status(self, status: Collection[SeedPlantingStatus]) -> list[SeedPlanting]:
        query = select(SeedPlanting).where(SeedPlanting.status.in_(status))
        return list((await self.session.scalars(query)).all())

    async def create(self, seed_planting: SeedPlanting) -> None:
        self.session.add(seed_planting)
        await self.session.flush()

    async def update(self, seed_planting: SeedPlanting, updates: dict[str, Any]) -> None:
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
        if "planted_on" in updates:
            seed_planting.planted_on = updates["planted_on"]
        if "germinated_first_on" in updates:
            seed_planting.germinated_first_on = updates["germinated_first_on"]
        if "count_planted" in updates:
            seed_planting.count_planted = updates["count_planted"]
        if "count_germinated" in updates:
            seed_planting.count_germinated = updates["count_germinated"]

        await self.session.flush()

    async def delete(self, seed_planting: SeedPlanting) -> None:
        await self.session.delete(seed_planting)
        await self.session.flush()
