from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from plants.exceptions import FlorescenceNotFoundError
from plants.modules.plant.models import Plant
from plants.modules.pollination.models import Florescence
from plants.shared.base_dal import BaseDAL

if TYPE_CHECKING:
    from collections.abc import Collection

    from plants.modules.pollination.enums import FlorescenceStatus


class FlorescenceDAL(BaseDAL):
    async def create_florescence(self, florescence: Florescence) -> None:
        self.session.add(florescence)
        await self.session.flush()

    async def delete_florescence(self, florescence: Florescence) -> None:
        await self.session.delete(florescence)
        await self.session.flush()

    async def by_status(self, status: Collection[FlorescenceStatus]) -> list[Florescence]:
        query = (
            select(Florescence)
            .options(selectinload(Florescence.plant).selectinload(Plant.taxon))
            .options(selectinload(Florescence.plant).selectinload(Plant.florescences))
            .where(Florescence.florescence_status.in_(status))
        )
        return list((await self.session.scalars(query)).all())

    async def get_all_florescences(self, *, include_inactive_plants: bool) -> list[Florescence]:
        query = (
            select(Florescence)
            .options(selectinload(Florescence.plant).selectinload(Plant.taxon))
            .options(selectinload(Florescence.plant).selectinload(Plant.florescences))
        )
        if not include_inactive_plants:
            query = query.join(Plant).where(Plant.active.is_(True))
        return list((await self.session.scalars(query)).all())

    async def by_id(self, florescence_id: int) -> Florescence:
        # noinspection PyTypeChecker
        query = (
            select(Florescence)
            .options(selectinload(Florescence.plant).selectinload(Plant.taxon))
            .options(selectinload(Florescence.pollinations))
            .where(Florescence.id == florescence_id)
        )
        florescence: Florescence | None = (await self.session.scalars(query)).first()
        if not florescence:
            raise FlorescenceNotFoundError(florescence_id)
        return florescence

    async def update_florescence(  # noqa: PLR0912 C901
        self, florescence: Florescence, updates: dict[str, Any]
    ) -> None:
        if "florescence_status" in updates:
            florescence.florescence_status = updates["florescence_status"]
        if "comment" in updates:
            florescence.comment = updates["comment"]
        if "branches_count" in updates:
            florescence.branches_count = updates["branches_count"]
        if "flowers_count" in updates:
            florescence.flowers_count = updates["flowers_count"]
        if "perianth_length" in updates:
            florescence.perianth_length = updates["perianth_length"]
        if "perianth_diameter" in updates:
            florescence.perianth_diameter = updates["perianth_diameter"]
        if "flower_color" in updates:
            florescence.flower_color = updates["flower_color"]
        if "flower_color_second" in updates:
            florescence.flower_color_second = updates["flower_color_second"]
        if "flower_colors_differentiation" in updates:
            florescence.flower_colors_differentiation = updates["flower_colors_differentiation"]
        if "stigma_position" in updates:
            florescence.stigma_position = updates["stigma_position"]

        if "first_flower_opened_at" in updates:
            florescence.first_flower_opened_at = updates["first_flower_opened_at"]
        if "last_flower_closed_at" in updates:
            florescence.last_flower_closed_at = updates["last_flower_closed_at"]
        if "inflorescence_appeared_at" in updates:
            florescence.inflorescence_appeared_at = updates["inflorescence_appeared_at"]
        if "last_update_context" in updates:
            florescence.last_update_context = updates["last_update_context"]

        if "self_pollinated" in updates:
            florescence.self_pollinated = updates["self_pollinated"]

        await self.session.flush()
