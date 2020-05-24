import logging

logger = logging.getLogger(__name__)

# class NamedPropertyPlantInfo(Base):
#     # todo check if renaming plant still works (i.e. updates here, too)
#     """new named properties - Plant specific infos - does it fulfill properties? Deviations?"""
#     __tablename__ = 'named_property_plant_info'
#     id = Column(INTEGER, primary_key=True, nullable=False, autoincrement=True)
#     plant_name = Column(CHAR(60), ForeignKey('plants.plant_name'), nullable=False)
#     property_name_id = Column(INTEGER, ForeignKey('property_name.id'), nullable=False)
#     named_property_id = Column(INTEGER, ForeignKey('named_property.id'), nullable=False)
#     match_status = Column(CHAR(30))  # e.g. "full", "partly"  todo possible values defined as constants
#     match_comment = Column(TEXT)