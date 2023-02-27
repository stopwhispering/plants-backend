from __future__ import annotations

from typing import TYPE_CHECKING

from plants.modules.image.models import Image, ImageKeyword, ImageToPlantAssociation

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from pathlib import PurePath

    from plants.modules.image.image_dal import ImageDAL
    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL


class ImageWriter:
    def __init__(self, plant_dal: PlantDAL, image_dal: ImageDAL):
        self.plant_dal = plant_dal
        self.image_dal = image_dal

    async def update_image_if_altered(
        self,
        image: Image,
        description: str,
        plant_ids: Sequence[int],
        keywords: Sequence[str],
    ):
        """compare current database record for image with supplied field values;
        update db entry if different;
        Note: record_date_time is only set at upload, so we're not comparing or
        updating it.
        """
        # description
        if description != image.description and not (
            not description and not image.description
        ):
            image.description = description

        # plants
        new_plants = {await self.plant_dal.by_id(plant_id) for plant_id in plant_ids}
        removed_image_to_plant_associations = [
            a for a in image.image_to_plant_associations if a.plant not in new_plants
        ]
        added_image_to_plant_associations = [
            ImageToPlantAssociation(
                image=image,
                plant=p,
            )
            for p in new_plants
            if p not in image.plants
        ]
        for removed_image_to_plant_association in removed_image_to_plant_associations:
            await self.plant_dal.delete_image_to_plant_association(
                removed_image_to_plant_association
            )
        if added_image_to_plant_associations:
            image.image_to_plant_associations.extend(added_image_to_plant_associations)

        # keywords
        current_keywords = {k.keyword for k in image.keywords}
        removed_keywords = [k for k in image.keywords if k.keyword not in keywords]
        added_keywords = [
            ImageKeyword(image_id=image.id, keyword=k)
            for k in set(keywords)
            if k not in current_keywords
        ]

        if removed_keywords:
            await self.image_dal.delete_keywords_from_image(image, removed_keywords)
        if added_keywords:
            await self.image_dal.create_new_keywords_for_image(image, added_keywords)

    async def create_image_in_db(
        self,
        relative_path: PurePath,
        record_date_time: datetime,
        keywords: Sequence[str],
        plants: list[Plant],
        # events and taxa are saved elsewhere
    ) -> Image:
        if await self.image_dal.get_image_by_relative_path(relative_path.as_posix()):
            raise ValueError(f"Image already exists in db: {relative_path.as_posix()}")

        image = Image(
            relative_path=relative_path.as_posix(),
            filename=relative_path.name,
            record_date_time=record_date_time,
            description=None,
            plants=plants if plants else [],
        )
        # get the image id
        await self.image_dal.create_image(image)
        image = await self.image_dal.by_id(image.id)

        if keywords:
            keywords_orm = [
                ImageKeyword(image_id=image.id, image=image, keyword=k)
                for k in keywords
            ]
            await self.image_dal.create_new_keywords_for_image(image, keywords_orm)
        return image
