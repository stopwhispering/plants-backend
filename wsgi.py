import logging

from plants_tagger.app import create_app
from plants_tagger.util.logger_utils import configure_root_logger


configure_root_logger()
logging.getLogger(__name__).info('Creating App.')
app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
    logging.getLogger(__name__).info('Starting App serving UWSGI.')
