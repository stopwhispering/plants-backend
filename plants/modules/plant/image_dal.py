from sqlalchemy import select

from plants.exceptions import ImageNotFound
from plants.modules.image.models import Image, ImageToEventAssociation, ImageToPlantAssociation, \
    ImageToTaxonAssociation, ImageKeyword
from plants.shared.base_dal import BaseDAL


class ImageDAL(BaseDAL):
    def __init__(self, session):
        super().__init__(session)

    def by_id(self, image_id: int) -> Image:
        query = (select(Image)
                 .where(Image.id == image_id)
                 .limit(1))
        image: Image = (self.session.scalars(query)).first()  # noqa
        if not image:
            raise ImageNotFound(image_id)
        return image

    def get_all_images(self) -> list[Image]:
        query = (select(Image)
                 )
        images: list[Image] = (self.session.scalars(query)).all()  # noqa
        return images

    def get_untagged_images(self) -> list[Image]:
        query = (select(Image)
                 .where(~Image.plants.any())
                 )
        images: list[Image] = (self.session.scalars(query)).all()  # noqa
        return images

    def get_distinct_image_keywords(self) -> set[str]:
        """get distinct keyword strings from ImageKeyword table"""
        query = (select(ImageKeyword.keyword)
                 .distinct(ImageKeyword.keyword)
                 )
        image_keywords: list[ImageKeyword] = (self.session.scalars(query)).all()  # noqa
        return set(image_keywords)

    def image_exists(self, filename: str) -> bool:
        query = (select(Image)
                 .where(Image.filename == filename)
                 .limit(1))
        image: Image = (self.session.scalars(query)).first()
        return image is not None

    def delete_image(self, image: Image):
        self.session.delete(image)
        self.session.flush()

    def get_image_by_filename(self, filename: str) -> Image:
        query = (select(Image)
                 .where(Image.filename == filename)
                 .limit(1))
        image: Image = (self.session.scalars(query)).first()
        if not image:
            raise ImageNotFound(filename)
        return image

    def get_image_by_relative_path(self, relative_path: str) -> Image | None:
        query = (select(Image)
                 .where(Image.relative_path == relative_path)
                 .limit(1))
        image: Image = (self.session.scalars(query)).first()
        return image

    def delete_image_by_filename(self, filename: str):
        query = (select(Image)
                 .where(Image.filename == filename)
                 .limit(1))
        image: Image = (self.session.scalars(query)).first()
        if not image:
            raise ImageNotFound(filename)
        self.session.delete(image)
        self.session.flush()

    def delete_image_to_event_associations(self, image: Image, links: list[ImageToEventAssociation]):
        for link in links:
            image.image_to_event_associations.remove(link)
            self.session.delete(link)
        self.session.flush()

    def delete_image_to_plant_associations(self, image: Image, links: list[ImageToPlantAssociation]):
        for link in links:
            image.image_to_plant_associations.remove(link)
            self.session.delete(link)
        self.session.flush()

    def delete_image_to_taxon_associations(self, image: Image, links: list[ImageToTaxonAssociation]):
        for link in links:
            image.image_to_taxon_associations.remove(link)
            self.session.delete(link)
        self.session.flush()

    def delete_keywords_from_image(self, image: Image, keywords: list[ImageKeyword]):
        for keyword in keywords:
            image.keywords.remove(keyword)
            self.session.delete(keyword)
        self.session.flush()

    def create_new_keywords_for_image(self, image: Image, keywords: list[ImageKeyword]):
        image.keywords.extend(keywords)
        self.session.add_all(keywords)
        self.session.flush()

    def create_image(self, image: Image):
        self.session.add(image)
        self.session.flush()
