from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest
import pytz
from dateutil.relativedelta import relativedelta

from plants.exceptions import SeedPlantingNotFoundError
from plants.modules.pollination.enums import SeedPlantingStatus
from plants.modules.pollination.schemas import SeedPlantingCreate, SeedPlantingUpdate
from plants.shared.api_constants import FORMAT_YYYY_MM_DD

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from plants.modules.event.models import Soil
    from plants.modules.pollination.models import Pollination, SeedPlanting
    from plants.modules.pollination.pollination_dal import PollinationDAL
    from plants.modules.pollination.seed_planting_dal import SeedPlantingDAL


@pytest.mark.usefixtures("seed_plantings_in_db", "trained_models")
@pytest.mark.asyncio()
async def test_list_seed_plantings(
    ac: AsyncClient,
    pollination_in_db: Pollination,
) -> None:
    response = await ac.get("/api/ongoing_pollinations")
    assert response.status_code == 200
    resp = response.json()
    pollinations = resp["ongoing_pollination_collection"]

    pollination = next(p for p in pollinations if p["id"] == pollination_in_db.id)
    seed_plantings = pollination["seed_plantings"]

    # seed_plantings has four entries:
    # one active,
    # one germinated one week ago,
    # one abandoned,
    # one germinated one year ago

    one_year_ago = (
        (datetime.now(tz=pytz.utc) - relativedelta(years=1)).date().strftime(FORMAT_YYYY_MM_DD)
    )  # e.g. "2022-05-03"
    one_week_ago = (
        (datetime.now(tz=pytz.utc) - relativedelta(days=7)).date().strftime(FORMAT_YYYY_MM_DD)
    )

    assert next(s for s in seed_plantings if s["status"] == SeedPlantingStatus.PLANTED.value)
    assert next(
        s
        for s in seed_plantings
        if s["status"] == SeedPlantingStatus.GERMINATED.value
        and s["germinated_first_on"] == one_week_ago
    )
    assert next(
        (s for s in seed_plantings if s["status"] == SeedPlantingStatus.ABANDONED.value), None
    )
    assert next(
        (
            s
            for s in seed_plantings
            if s["status"] == SeedPlantingStatus.GERMINATED.value
            and s["germinated_first_on"] == one_year_ago
        ),
        None,
    )
    assert len(seed_plantings) == 4


@pytest.mark.asyncio()
async def test_delete_seed_planting(
    ac: AsyncClient,
    seed_plantings_in_db: list[SeedPlanting],
    seed_planting_dal: SeedPlantingDAL,
) -> None:
    # seed_plantings_in_db has four entries; we delete the active one
    seed_planting_in_db = next(
        s for s in seed_plantings_in_db if s.status == SeedPlantingStatus.PLANTED
    )
    seed_planting_id = seed_planting_in_db.id
    response = await ac.delete(f"/api/seed_plantings/{seed_planting_id}")
    assert response.status_code == 200

    # check that seed planting is no longer in db (it is actually deleted, there
    # is no "deleted" flag)
    with pytest.raises(SeedPlantingNotFoundError):
        _ = await seed_planting_dal.by_id(seed_planting_id)


@pytest.mark.asyncio()
async def test_update_seed_planting(
    ac: AsyncClient,
    test_db: AsyncSession,
    seed_plantings_in_db: list[SeedPlanting],
    # seed_planting_dal: SeedPlantingDAL,
) -> None:
    # seed_plantings_in_db has four entries; we update the active one
    seed_planting_in_db = next(
        s for s in seed_plantings_in_db if s.status == SeedPlantingStatus.PLANTED
    )

    today = datetime.now(tz=pytz.utc).date()
    yesterday = (datetime.now(tz=pytz.utc) - relativedelta(days=1)).date()
    payload = SeedPlantingUpdate(
        id=seed_planting_in_db.id,
        status=SeedPlantingStatus.GERMINATED,
        count_germinated=10,
        germinated_first_on=today,
        pollination_id=seed_planting_in_db.pollination_id,
        comment="Updated seed planting",
        sterilized=not seed_planting_in_db.sterilized,
        soaked=not seed_planting_in_db.soaked,
        covered=not seed_planting_in_db.covered,
        planted_on=yesterday,
        count_planted=100,
        soil_id=seed_planting_in_db.soil_id,
        abandoned_on=None,
    )
    response = await ac.put(
        f"/api/seed_plantings/{seed_planting_in_db.id}",
        json=payload.dict()
        | {
            "planted_on": yesterday.strftime(FORMAT_YYYY_MM_DD),
            "germinated_first_on": today.strftime(FORMAT_YYYY_MM_DD),
        },
    )
    assert response.status_code == 200

    # refetch from db
    await test_db.refresh(seed_planting_in_db)

    assert seed_planting_in_db.status == payload.status
    assert seed_planting_in_db.count_germinated == payload.count_germinated
    assert seed_planting_in_db.germinated_first_on == today
    assert seed_planting_in_db.pollination_id == payload.pollination_id
    assert seed_planting_in_db.comment == payload.comment
    assert seed_planting_in_db.sterilized == payload.sterilized
    assert seed_planting_in_db.soaked == payload.soaked
    assert seed_planting_in_db.covered == payload.covered
    assert seed_planting_in_db.planted_on == yesterday
    assert seed_planting_in_db.count_planted == payload.count_planted


@pytest.mark.asyncio()
async def test_create_seed_planting(
    ac: AsyncClient,
    pollination_in_db: Pollination,
    pollination_dal: PollinationDAL,
    soil_in_db: Soil,
) -> None:
    today = datetime.now(tz=pytz.utc).date().strftime(FORMAT_YYYY_MM_DD)
    payload = SeedPlantingCreate(
        status=SeedPlantingStatus.PLANTED,
        pollination_id=pollination_in_db.id,
        comment="new seed planting from pollination",
        sterilized=False,
        soaked=False,
        covered=True,
        planted_on=today,  # type: ignore[arg-type]
        count_planted=5,
        soil_id=soil_in_db.id,
    )
    response = await ac.post("/api/seed_plantings", json=payload.dict() | {"planted_on": today})
    assert response.status_code == 200

    # refetch the pollination to get the new seed planting
    await pollination_dal.by_id(pollination_in_db.id)

    assert len(pollination_in_db.seed_plantings) == 1
    seed_planting_in_db = pollination_in_db.seed_plantings[0]
    assert seed_planting_in_db.planted_on == datetime.now(tz=pytz.utc).date()
    assert seed_planting_in_db.comment == payload.comment
    assert seed_planting_in_db.sterilized == payload.sterilized
    assert seed_planting_in_db.soaked == payload.soaked
    assert seed_planting_in_db.covered == payload.covered
    assert seed_planting_in_db.count_planted == payload.count_planted
    assert seed_planting_in_db.soil_id == payload.soil_id
