from flask import Flask
from flask_restful import Api
import logging

from plants_tagger.extensions.orm import init_sqlalchemy_engine
from plants_tagger.models.event_models import insert_categories
from plants_tagger.models.property_models import insert_property_categories
from plants_tagger.resources.event_resource import EventResource
from plants_tagger.resources.image_resource import ImageResource
# from plants_tagger.resources.named_property_resource import PropertyResource
from plants_tagger.resources.property_name_resource import PropertyNameResource
from plants_tagger.resources.property_resources import PropertyResource, PropertyTaxaResource
from plants_tagger.resources.plant_resource import PlantResource
from plants_tagger.resources.proposal_resource import ProposalResource
from plants_tagger.resources.refresh_photo_dir_resource import RefreshPhotoDirectoryResource
from plants_tagger.resources.taxon_resoure import TaxonResource
from plants_tagger.resources.taxon_to_plant_assignments_resource import TaxonToPlantAssignmentsResource
from plants_tagger.config_local import ALLOW_CORS

logger = logging.getLogger(__name__)


# factory
def create_app():
    app = Flask(__name__)
    api = Api(app)

    init_sqlalchemy_engine([insert_categories, insert_property_categories])

    # allow cors only for testing purposes
    if ALLOW_CORS:
        @app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response

    api.add_resource(PlantResource, '/plants_tagger/backend/Plant/<string:plant_name>',
                                    '/plants_tagger/backend/Plant')
    api.add_resource(ImageResource, '/plants_tagger/backend/Image')
    api.add_resource(RefreshPhotoDirectoryResource, '/plants_tagger/backend/RefreshPhotoDirectory')
    api.add_resource(TaxonToPlantAssignmentsResource, '/plants_tagger/backend/SpeciesDatabase')
    api.add_resource(TaxonResource, '/plants_tagger/backend/Taxon')
    api.add_resource(EventResource, '/plants_tagger/backend/Event/<string:plant_name>',  # only get
                                    '/plants_tagger/backend/Event')  # only post
    api.add_resource(ProposalResource, '/plants_tagger/backend/Proposal/<string:entity_id>')

    api.add_resource(PropertyResource, '/plants_tagger/backend/Property/<string:plant_id>',
                                       '/plants_tagger/backend/Property')  # only post)
    api.add_resource(PropertyTaxaResource, '/plants_tagger/backend/PropertyTaxon')  # only post

    api.add_resource(PropertyNameResource, '/plants_tagger/backend/PropertyName')

    logger.info('Added REST Resources.')

    return app
