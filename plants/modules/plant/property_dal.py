# from sqlalchemy import select
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from plants.exceptions import PropertyCategoryNotFound, PropertyValueNotFound
from plants.modules.property.models import PropertyValue, PropertyCategory, PropertyName
# from plants.modules.event.models import Event
from plants.shared.base_dal import BaseDAL


class PropertyDAL(BaseDAL):
    def __init__(self, session):
        super().__init__(session)

    # def create(self, events: list[Property]):
    #     self.session.add_all(events)
    #     self.session.flush()

    def create_property_values(self, property_values: list[PropertyValue]):
        self.session.add_all(property_values)
        self.session.flush()

    def delete_property_values(self, property_values: list[PropertyValue]):
        for property_value in property_values:
            self.session.delete(property_value)
        self.session.flush()

    def delete_property_value(self, property_value: PropertyValue):
        self.session.delete(property_value)
        self.session.flush()

    def create_property_name(self, property_name: PropertyName):
        self.session.add_all(property_name)
        self.session.flush()

    def get_property_values_by_plant_id(self, plant_id: int) -> list[PropertyValue]:
        query = (select(PropertyValue)
                 .where(PropertyValue.plant_id == plant_id)
                 .where(PropertyValue.taxon_id.is_(None))
                 )
        property_values: list[PropertyValue] = (self.session.scalars(query)).all()  # noqa
        return property_values

    def get_all_property_categories(self) -> list[PropertyCategory]:
        query = (select(PropertyCategory)
                 .options(selectinload(PropertyCategory.property_names))
                 )
        property_categories: list[PropertyCategory] = (self.session.scalars(query)).all()  # noqa
        return property_categories

    def get_property_category_by_id(self, property_category_id: int) -> PropertyCategory:
        query = (select(PropertyCategory)
                 .where(PropertyCategory.id == property_category_id)
                 .limit(1))
        property_category: PropertyCategory = (self.session.scalars(query)).first()
        if not property_category:
            raise PropertyCategoryNotFound(property_category_id)
        return property_category

    def get_property_value_by_id(self, property_value_id: int) -> PropertyValue:
        query = (select(PropertyValue)
                 .where(PropertyValue.id == property_value_id)
                 .limit(1))
        property_value: PropertyValue = (self.session.scalars(query)).first()
        if not property_value:
            raise PropertyValueNotFound(property_value_id)
        return property_value

    def get_property_category_by_name(self, property_category_name: str) -> PropertyCategory:
        query = (select(PropertyCategory)
                 .where(PropertyCategory.category_name == property_category_name)
                 .limit(1))
        property_category: PropertyCategory = (self.session.scalars(query)).first()
        if not property_category:
            raise PropertyCategoryNotFound(property_category_name)
        return property_category
