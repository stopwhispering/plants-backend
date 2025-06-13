from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from plants.exceptions import CriterionNotImplementedError, PollinationNotFoundError
from plants.modules.plant.models import Plant
from plants.modules.pollination.enums import COLORS_MAP_TO_RGB, FlorescenceStatus, PollinationStatus
from plants.modules.pollination.models import Florescence, Pollination, SeedPlanting
from plants.shared.base_dal import BaseDAL


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

    async def get_pollinations(
        self,
        *,
        include_ongoing_pollinations: bool,
        include_finished_pollinations: bool,
    ) -> list[Pollination]:
        # noinspection PyTypeChecker
        query = (
            select(Pollination)
            .join(Pollination.florescence)  # can't filter on Florescence attr otherwise
            .options(
                selectinload(Pollination.seed_capsule_plant).selectinload(Plant.taxon),
                selectinload(Pollination.pollen_donor_plant).selectinload(Plant.taxon),
                selectinload(Pollination.seed_plantings)
                .selectinload(SeedPlanting.pollination)
                .selectinload(Pollination.seed_capsule_plant),
                selectinload(Pollination.seed_plantings)
                .selectinload(SeedPlanting.pollination)
                .selectinload(Pollination.pollen_donor_plant),
                selectinload(Pollination.seed_plantings)
                .selectinload(SeedPlanting.plants)
                .selectinload(Plant.taxon),
                selectinload(Pollination.seed_plantings).selectinload(SeedPlanting.soil),
                selectinload(Pollination.florescence).selectinload(Florescence.pollinations),
            )
        )

        if not include_ongoing_pollinations and not include_finished_pollinations:
            return []
        if include_ongoing_pollinations and not include_finished_pollinations:
            # query = query.where(
            #     or_(
            #         Pollination.ongoing,
            #         Florescence.florescence_status == FlorescenceStatus.FLOWERING,
            #     ),
            # )
            query = query.where(
                or_(
                    Pollination.ongoing.is_(True),
                    Florescence.florescence_status == FlorescenceStatus.FLOWERING,
                    Pollination.florescence.has(
                        Florescence.pollinations.any(Pollination.ongoing.is_(True))
                    ),
                )
            )
        elif include_finished_pollinations and not include_ongoing_pollinations:
            query = query.where(Pollination.ongoing.is_(False))
        # else: no filter

        # for legacy reasons, we need to filter out pollinations where
        # the seed capsule plant's taxon is None
        query = query.where(
            Pollination.seed_capsule_plant.has(Plant.taxon_id.is_not(None)),
            Pollination.pollen_donor_plant.has(Plant.taxon_id.is_not(None)),
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
            elif key == "seed_capsule_plant_id":
                query = query.where(Pollination.seed_capsule_plant_id == value)
            elif key == "pollen_donor_plant":
                query = query.where(Pollination.pollen_donor_plant == value)
            elif key == "pollen_donor_plant_id":
                query = query.where(Pollination.pollen_donor_plant_id == value)
            elif key == "label_color":
                query = query.where(Pollination.label_color == value)
            elif key == "florescence_id":
                query = query.where(Pollination.florescence_id == value)
            else:
                raise CriterionNotImplementedError(key)

        pollinations: list[Pollination] = list((await self.session.scalars(query)).all())
        return pollinations

    async def get_pollinations_by_plants(
        self, seed_capsule_plant_id: int, pollen_donor_plant_id: int
    ) -> list[Pollination]:
        # noinspection PyTypeChecker
        query = (
            select(Pollination)
            .where(
                Pollination.seed_capsule_plant_id == seed_capsule_plant_id,
                Pollination.pollen_donor_plant_id == pollen_donor_plant_id,
            )
            .options(
                selectinload(Pollination.seed_plantings).selectinload(SeedPlanting.soil),
                selectinload(Pollination.seed_plantings)
                .selectinload(SeedPlanting.plants)
                .selectinload(Plant.taxon),
                selectinload(Pollination.florescence),
            )
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
