from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TCH002
from sqlalchemy.orm import selectinload

from plants.exceptions import ImageNotFoundError
from plants.modules.image.models import (
    Image,
    ImageKeyword,
    ImageToEventAssociation,
    ImageToPlantAssociation,
    ImageToTaxonAssociation,
)
from plants.shared.base_dal import BaseDAL


class ImageDAL(BaseDAL):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    @staticmethod
    def _add_eager_load_options(query: Select[Any]) -> Select[Any]:
        """Apply eager loading the query supplied; use only for single- or limited-
        number select queries to avoid performance issues."""
        return query.options(
            selectinload(Image.keywords),
            selectinload(Image.plants),
            selectinload(Image.image_to_plant_associations),
            selectinload(Image.plants),
            selectinload(Image.image_to_event_associations),
            selectinload(Image.events),
            selectinload(Image.image_to_taxon_associations),
            selectinload(Image.taxa),
            selectinload(Image.keywords),
        )

    async def by_id(self, image_id: int) -> Image:
        # noinspection PyTypeChecker
        query = select(Image).where(Image.id == image_id).limit(1)
        query = self._add_eager_load_options(query)
        image: Image | None = (await self.session.scalars(query)).first()
        if not image:
            raise ImageNotFoundError(image_id)
        return image

    async def by_ids(self, image_ids: list[int]) -> list[Image]:
        query = select(Image).where(Image.id.in_(image_ids))
        query = self._add_eager_load_options(query)
        images: list[Image] = list((await self.session.scalars(query)).all())
        return images

    async def get_image_by_filename(self, filename: str) -> Image:
        # noinspection PyTypeChecker
        query = select(Image).where(Image.filename == filename).limit(1)
        query = self._add_eager_load_options(query)
        image: Image | None = (await self.session.scalars(query)).first()
        if not image:
            raise ImageNotFoundError(filename)
        return image

    async def get_all_images(self) -> list[Image]:
        query = select(Image)
        images: list[Image] = list((await self.session.scalars(query)).all())
        return images

    async def get_untagged_images(self) -> list[Image]:
        query = (
            select(Image)
            .where(~Image.plants.any())
            .options(selectinload(Image.keywords))
            .options(selectinload(Image.plants))
        )
        images: list[Image] = list((await self.session.scalars(query)).all())
        return images

    async def get_distinct_image_keywords(self) -> set[str]:
        """Get distinct keyword strings from ImageKeyword table."""
        # noinspection PyTypeChecker
        query = select(ImageKeyword.keyword).distinct(ImageKeyword.keyword)
        image_keywords: list[str] = list((await self.session.scalars(query)).all())
        return set(image_keywords)

    async def image_exists(self, filename: str) -> bool:
        # noinspection PyTypeChecker
        query = select(Image).where(Image.filename == filename).limit(1)
        image: Image | None = (await self.session.scalars(query)).first()
        return image is not None

    async def delete_image(self, image: Image) -> None:
        await self.session.delete(image)
        await self.session.flush()

    async def get_image_by_relative_path(self, relative_path: str) -> Image | None:
        # noinspection PyTypeChecker
        query = select(Image).where(Image.relative_path == relative_path).limit(1)
        image: Image | None = (await self.session.scalars(query)).first()
        return image

    async def delete_image_by_filename(self, filename: str) -> None:
        # noinspection PyTypeChecker
        query = select(Image).where(Image.filename == filename).limit(1)
        image: Image | None = (await self.session.scalars(query)).first()
        if not image:
            raise ImageNotFoundError(filename)
        await self.session.delete(image)
        await self.session.flush()

    async def delete_image_to_event_associations(
        self, image: Image, links: list[ImageToEventAssociation]
    ) -> None:
        for link in links:
            image.image_to_event_associations.remove(link)
            await self.session.delete(link)
        await self.session.flush()

    async def delete_image_to_plant_associations(
        self, image: Image, links: list[ImageToPlantAssociation]
    ) -> None:
        for link in links:
            image.image_to_plant_associations.remove(link)
            await self.session.delete(link)
        await self.session.flush()

    async def delete_image_to_taxon_associations(
        self, image: Image, links: list[ImageToTaxonAssociation]
    ) -> None:
        for link in links:
            image.image_to_taxon_associations.remove(link)
            await self.session.delete(link)
        await self.session.flush()

    async def delete_keywords_from_image(
        self, image: Image, keywords: list[ImageKeyword]
    ) -> None:
        for keyword in keywords:
            image.keywords.remove(keyword)
            await self.session.delete(keyword)
        await self.session.flush()

    async def create_new_keywords_for_image(
        self, image: Image, keywords: list[ImageKeyword]
    ) -> None:
        image.keywords.extend(keywords)
        self.session.add_all(keywords)
        await self.session.flush()

    async def create_image(self, image: Image) -> None:
        self.session.add(image)
        await self.session.flush()
