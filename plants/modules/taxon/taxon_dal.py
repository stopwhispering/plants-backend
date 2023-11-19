from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    String,
    delete,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.operators import and_

from plants.exceptions import (
    CriterionNotImplementedError,
    TaxonNotFoundError,
)
from plants.modules.image.models import Image, ImageToTaxonAssociation
from plants.modules.plant.models import Plant
from plants.modules.taxon.models import (
    Taxon,
    TaxonOccurrenceImage,
    TaxonToOccurrenceAssociation,
)
from plants.shared.base_dal import BaseDAL

if TYPE_CHECKING:
    from plants.modules.taxon.enums import FBRank


# TaxaWithPlantIds = tuple[list[tuple[str, str, str | None, int, list[int]]],
TaxaWithPlantIds = list[tuple[Taxon, list[int]]]


class TaxonDAL(BaseDAL):
    async def by_id(self, taxon_id: int) -> Taxon:
        # noinspection PyTypeChecker
        query = (
            select(Taxon)
            .where(Taxon.id == taxon_id)
            .options(selectinload(Taxon.occurrence_images))
            .options(
                selectinload(Taxon.images).selectinload(Image.image_to_taxon_associations),
                # selectinload(Taxon.image_to_taxon_associations),
            )
            .options(selectinload(Taxon.distribution))
            .limit(1)
        )
        # noinspection PyTypeChecker
        taxon: Taxon | None = (await self.session.scalars(query)).first()
        if not taxon:
            raise TaxonNotFoundError(taxon_id)
        return taxon

    def expire_all(self) -> None:
        self.session.expire_all()

    async def by_gbif_id(self, gbif_id: int) -> list[Taxon]:
        # noinspection PyTypeChecker
        query = (
            select(Taxon)
            .where(Taxon.gbif_id == gbif_id)
            .options(selectinload(Taxon.occurrence_images))
        )

        taxa: list[Taxon] = list((await self.session.scalars(query)).all())
        return taxa

    async def get_taxa_by_name_pattern(
        self, taxon_name_pattern: str, rank: FBRank | None = None
    ) -> list[Taxon]:
        query = (
            select(Taxon)
            .where(Taxon.name.ilike(taxon_name_pattern))  # ilike ~ case-insensitive like
            .options(selectinload(Taxon.plants))
        )
        if rank:
            query = query.where(Taxon.rank == rank.value)
        taxa: list[Taxon] = list((await self.session.scalars(query)).all())
        return taxa

    async def get_taxon_occurrence_image_by_filter(
        self, criteria: dict[str, Any]
    ) -> list[TaxonOccurrenceImage]:
        query = select(TaxonOccurrenceImage)
        for key, value in criteria.items():
            if key == "gbif_id":
                query = query.where(TaxonOccurrenceImage.gbif_id == value)
            elif key == "occurrence_id":
                query = query.where(TaxonOccurrenceImage.occurrence_id == value)
            elif key == "img_no":
                query = query.where(TaxonOccurrenceImage.img_no == value)
            else:
                raise CriterionNotImplementedError(key)

        images: list[TaxonOccurrenceImage] = list((await self.session.scalars(query)).all())
        return images

    async def fetch_taxa_with_plant_ids(
        self,
    ) -> TaxaWithPlantIds:
        plant_exists_filter = and_(Plant.deleted.is_(False), Plant.active)
        has_any_plant_filter = Taxon.plants.any(plant_exists_filter)

        # array_agg seems to not work with int array, so we need to cast to string
        # this will, however, return a list of int not string
        # pylint: disable=not-callable
        plant_ids_agg = func.array_agg(Plant.id, type_=ARRAY(String))
        query = select(Taxon, plant_ids_agg)
        query = query.join(Taxon.plants)
        query = query.where(has_any_plant_filter)
        query = query.group_by(Taxon)  # type:ignore[arg-type]
        query = query.order_by(Taxon.family, Taxon.genus, Taxon.species)
        taxa_with_plant_ids: TaxaWithPlantIds = list(
            (await self.session.execute(query)).all()  # type:ignore[arg-type]
        )
        return taxa_with_plant_ids

    async def create_taxon_to_occurrence_associations(
        self, links: list[TaxonToOccurrenceAssociation]
    ) -> None:
        self.session.add_all(links)
        await self.session.flush()

    async def create_taxon_occurrence_images(
        self, occurrence_images: list[TaxonOccurrenceImage]
    ) -> None:
        self.session.add_all(occurrence_images)
        await self.session.flush()

    async def create_image_to_taxon_association(
        self, image_to_taxon_association: ImageToTaxonAssociation
    ) -> None:
        self.session.add(image_to_taxon_association)
        await self.session.flush()

    async def delete_taxon_to_occurrence_associations_by_gbif_id(self, gbif_id: int) -> None:
        query = delete(TaxonToOccurrenceAssociation).where(
            TaxonToOccurrenceAssociation.gbif_id == gbif_id
        )
        await self.session.execute(query)
        await self.session.flush()

    async def delete_taxon_occurrence_image_by_gbif_id(self, gbif_id: int) -> None:
        # noinspection PyTypeChecker
        query = delete(TaxonOccurrenceImage).where(TaxonOccurrenceImage.gbif_id == gbif_id)
        await self.session.execute(query)
        await self.session.flush()

    async def fetch_image_to_taxon_association(
        self, image_id: int, taxon_id: int
    ) -> ImageToTaxonAssociation | None:
        query = select(ImageToTaxonAssociation)
        query = query.where(
            and_(  # type:ignore[arg-type]
                ImageToTaxonAssociation.image_id == image_id,
                ImageToTaxonAssociation.taxon_id == taxon_id,
            )
        )
        link: ImageToTaxonAssociation | None = (await self.session.scalars(query)).first()
        return link

    async def exists(self, taxon_name: str) -> bool:
        # noinspection PyTypeChecker
        query = select(Taxon).where(Taxon.name == taxon_name).limit(1)
        taxon: Taxon | None = (await self.session.scalars(query)).first()
        return taxon is not None

    async def create(self, taxon: Taxon) -> None:
        self.session.add(taxon)
        await self.session.flush()

    async def update(self, taxon: Taxon, updates: dict[str, Any]) -> None:
        if "custom_notes" in updates:
            taxon.custom_notes = updates["custom_notes"]

        await self.session.flush()
