from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.operators import and_

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from plants.exceptions import (
    CriterionNotImplementedError,
    ImageNotAssignedToTaxonError,
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


class TaxonDAL(BaseDAL):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def by_id(self, taxon_id: int) -> Taxon:
        query = (
            select(Taxon)
            .where(Taxon.id == taxon_id)  # noqa
            .options(selectinload(Taxon.occurrence_images))
            .options(
                selectinload(Taxon.images).selectinload(
                    Image.image_to_taxon_associations
                )
            )
            .options(selectinload(Taxon.distribution))
            .limit(1)
        )
        taxon: Taxon = (await self.session.scalars(query)).first()  # noqa
        if not taxon:
            raise TaxonNotFoundError(taxon_id)
        return taxon

    async def by_gbif_id(self, gbif_id: int) -> list[Taxon]:
        query = select(Taxon).where(Taxon.gbif_id == gbif_id)  # noqa
        taxa: list[Taxon] = (await self.session.scalars(query)).all()  # noqa
        return taxa

    async def get_taxa_by_name_pattern(
        self, taxon_name_pattern: str, rank: FBRank = None
    ) -> list[Taxon]:
        query = (
            select(Taxon)
            .where(
                Taxon.name.ilike(taxon_name_pattern)
            )  # ilike ~ case-insensitive like
            .options(selectinload(Taxon.plants))
        )
        if rank:
            query = query.where(Taxon.rank == rank.value)  # noqa
        taxa: list[Taxon] = (await self.session.scalars(query)).all()  # noqa
        return taxa

    async def get_taxon_occurrence_image_by_filter(
        self, criteria: dict
    ) -> list[TaxonOccurrenceImage]:
        query = select(TaxonOccurrenceImage)
        for key, value in criteria.items():
            if key == "gbif_id":
                value: int
                query = query.where(TaxonOccurrenceImage.gbif_id == value)
            elif key == "occurrence_id":
                value: int
                query = query.where(TaxonOccurrenceImage.occurrence_id == value)
            elif key == "img_no":
                value: int
                query = query.where(TaxonOccurrenceImage.img_no == value)
            else:
                raise CriterionNotImplementedError(key)

        images: list[TaxonOccurrenceImage] = (
            await self.session.scalars(query)
        ).all()  # noqa
        return images

    async def get_distinct_species_as_tuples(self) -> tuple[str, str, str, int]:
        # todo performance optimize
        plant_exists_filter = and_(
            Plant.deleted.is_(False), Plant.active  # noqa FBT003
        )  # noqa FBT003
        has_any_plant_filter = Taxon.plants.any(plant_exists_filter)

        query = select(Taxon.family, Taxon.genus, Taxon.species, Taxon.id).where(
            has_any_plant_filter
        )
        species_tuples = (await self.session.execute(query)).all()
        return species_tuples  # noqa

    async def create_taxon_to_occurrence_associations(
        self, links: list[TaxonToOccurrenceAssociation]
    ):
        self.session.add_all(links)
        await self.session.flush()

    async def create_taxon_occurrence_images(
        self, occurrence_images: list[TaxonOccurrenceImage]
    ):
        self.session.add_all(occurrence_images)
        await self.session.flush()

    async def create_image_to_taxon_association(
        self, image_to_taxon_association: list[ImageToTaxonAssociation]
    ):
        self.session.add(image_to_taxon_association)
        await self.session.flush()

    async def delete_taxon_to_occurrence_associations_by_gbif_id(self, gbif_id: int):
        query = delete(TaxonToOccurrenceAssociation).where(
            TaxonToOccurrenceAssociation.gbif_id == gbif_id
        )
        await self.session.execute(query)
        await self.session.flush()

    async def delete_taxon_occurrence_image_by_gbif_id(self, gbif_id: int):
        query = delete(TaxonOccurrenceImage).where(
            TaxonOccurrenceImage.gbif_id == gbif_id
        )
        await self.session.execute(query)
        await self.session.flush()

    async def delete_image_association_from_taxon(
        self, taxon: Taxon, link: ImageToTaxonAssociation
    ):
        if link not in taxon.image_to_taxon_associations:
            raise ImageNotAssignedToTaxonError(taxon.id, link.image_id)
        taxon.image_to_taxon_associations.remove(link)

        await self.session.delete(link)
        await self.session.flush()

    async def exists(self, taxon_name: str) -> bool:
        query = select(Taxon).where(Taxon.name == taxon_name).limit(1)  # noqa
        taxon: Taxon = (await self.session.scalars(query)).first()  # noqa
        return taxon is not None

    async def create(self, taxon: Taxon):
        self.session.add(taxon)
        await self.session.flush()

    async def update(self, taxon: Taxon, updates: dict):
        if "custom_notes" in updates:
            taxon.custom_notes = updates["custom_notes"]

        await self.session.flush()
