from typing import Collection

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from plants.exceptions import FlorescenceNotFound
from plants.modules.plant.models import Plant
from plants.modules.pollination.models import Florescence
from plants.modules.pollination.enums import FlorescenceStatus
from plants.shared.base_dal import BaseDAL


class FlorescenceDAL(BaseDAL):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_florescence(self, florescence: Florescence):
        self.session.add(florescence)
        await self.session.flush()

    async def delete_florescence(self, florescence: Florescence):
        await self.session.delete(florescence)
        await self.session.flush()

    async def by_status(self, status: Collection[FlorescenceStatus]) -> list[Florescence]:
        query = (
            select(Florescence)
            .options(selectinload(Florescence.plant).selectinload(Plant.taxon))
            .options(selectinload(Florescence.plant).selectinload(Plant.florescences))
            .where(Florescence.florescence_status.in_(status))
        )
        return (await self.session.scalars(query)).all()  # noqa

    async def by_id(self, florescence_id: int) -> Florescence:
        query = (
            select(Florescence)
            .options(selectinload(Florescence.plant))
            .where(Florescence.id == florescence_id)  # noqa
        )
        florescence: Florescence = (await self.session.scalars(query)).first()
        if not florescence:
            raise FlorescenceNotFound(florescence_id)
        return florescence

    async def update_florescence(self, florescence: Florescence, updates: dict):
        if 'florescence_status' in updates:
            florescence.florescence_status = updates['florescence_status']
        if 'comment' in updates:
            florescence.comment = updates['comment']
        if 'branches_count' in updates:
            florescence.branches_count = updates['branches_count']
        if 'flowers_count' in updates:
            florescence.flowers_count = updates['flowers_count']
        if 'perianth_length' in updates:
            florescence.perianth_length = updates['perianth_length']
        if 'perianth_diameter' in updates:
            florescence.perianth_diameter = updates['perianth_diameter']
        if 'flower_color' in updates:
            florescence.flower_color = updates['flower_color']
        if 'flower_color_second' in updates:
            florescence.flower_color_second = updates['flower_color_second']
        if 'flower_colors_differentiation' in updates:
            florescence.flower_colors_differentiation = updates['flower_colors_differentiation']
        if 'stigma_position' in updates:
            florescence.stigma_position = updates['stigma_position']

        if 'first_flower_opening_date' in updates:
            florescence.first_flower_opening_date = updates['first_flower_opening_date']
        if 'last_flower_closing_date' in updates:
            florescence.last_flower_closing_date = updates['last_flower_closing_date']
        if 'inflorescence_appearance_date' in updates:
            florescence.inflorescence_appearance_date = updates['inflorescence_appearance_date']
        if 'last_update_context' in updates:
            florescence.last_update_context = updates['last_update_context']

        await self.session.flush()
