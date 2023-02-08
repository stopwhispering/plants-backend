from sqlalchemy import select
from sqlalchemy.orm import selectinload

from plants.exceptions import PropertyCategoryNotFound, PropertyValueNotFound
from plants.modules.property.models import PropertyValue, PropertyCategory, PropertyName
from plants.shared.base_dal import BaseDAL


class PropertyDAL(BaseDAL):
    def __init__(self, session):
        super().__init__(session)

    async def create_property_values(self, property_values: list[PropertyValue]):
        self.session.add_all(property_values)
        await self.session.flush()

    async def delete_property_values(self, property_values: list[PropertyValue]):
        for property_value in property_values:
            await self.session.delete(property_value)
        await self.session.flush()

    async def delete_property_value(self, property_value: PropertyValue):
        await self.session.delete(property_value)
        await self.session.flush()

    async def create_property_name(self, property_name: PropertyName):
        self.session.add_all(property_name)
        await self.session.flush()

    async def get_property_values_by_plant_id(self, plant_id: int) -> list[PropertyValue]:
        query = (select(PropertyValue)
                 .where(PropertyValue.plant_id == plant_id)
                 .where(PropertyValue.taxon_id.is_(None))
                 )
        property_values: list[PropertyValue] = (await self.session.scalars(query)).all()  # noqa
        return property_values

    async def get_all_property_categories(self) -> list[PropertyCategory]:
        query = (select(PropertyCategory)
                 .options(selectinload(PropertyCategory.property_names).selectinload(PropertyName.property_values))
                 )
        property_categories: list[PropertyCategory] = (await self.session.scalars(query)).all()  # noqa
        return property_categories

    async def get_property_category_by_id(self, property_category_id: int) -> PropertyCategory:
        query = (select(PropertyCategory)
                 .where(PropertyCategory.id == property_category_id)
                 .limit(1))
        property_category: PropertyCategory = (await self.session.scalars(query)).first()
        if not property_category:
            raise PropertyCategoryNotFound(property_category_id)
        return property_category

    async def get_property_value_by_id(self, property_value_id: int) -> PropertyValue:
        query = (select(PropertyValue)
                 .where(PropertyValue.id == property_value_id)
                 .limit(1))
        property_value: PropertyValue = (await self.session.scalars(query)).first()
        if not property_value:
            raise PropertyValueNotFound(property_value_id)
        return property_value

    async def get_property_category_by_name(self, property_category_name: str) -> PropertyCategory:
        query = (select(PropertyCategory)
                 .where(PropertyCategory.category_name == property_category_name)
                 .limit(1))
        property_category: PropertyCategory = (await self.session.scalars(query)).first()
        if not property_category:
            raise PropertyCategoryNotFound(property_category_name)
        return property_category
