from flask import Flask
from flask_restful import Api
import logging

# from plants_tagger.models.orm_tables import Plant
from plants_tagger.resources.image_resource import ImageResource
from plants_tagger.resources.image_resource_2 import ImageResource2
from plants_tagger.resources.plant_resource import PlantResource
from plants_tagger.resources.refresh_photo_directory_resource import RefreshPhotoDirectoryResource
from plants_tagger.resources.taxon_resoure import TaxonResource
from plants_tagger.resources.taxon_to_plant_assignments_resource import TaxonToPlantAssignmentsResource
from plants_tagger.resources.species_resource import SpeciesResource

logger = logging.getLogger(__name__)


def create_app():
    # pass
    app = Flask(__name__)
    # update the flask config dict
    # app.config.from_object(config)
    # app.config.update(DEBUG=False,  # unfortunately required to allow breakpoint to work
    #                   PROPAGATE_EXCEPTIONS=True)  # enable without debugging mode

    api = Api(app)

    # allow cors
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    # api.add_resource(ImageResource, '/plants_tagger/backend/Image')
    api.add_resource(PlantResource, '/plants_tagger/backend/Plant')
    api.add_resource(ImageResource2, '/plants_tagger/backend/Image2')
    api.add_resource(ImageResource, '/plants_tagger/backend/Image')
    api.add_resource(RefreshPhotoDirectoryResource, '/plants_tagger/backend/RefreshPhotoDirectory')
    api.add_resource(SpeciesResource, '/plants_tagger/backend/Species')  # todo remove
    api.add_resource(TaxonToPlantAssignmentsResource, '/plants_tagger/backend/SpeciesDatabase')
    api.add_resource(TaxonResource, '/plants_tagger/backend/Taxon')
    logger.info('Added REST Resources.')

    return app
