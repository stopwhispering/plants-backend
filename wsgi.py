import logging
import threading

from plants_tagger.app import create_app
from plants_tagger.models.photo_dir_watchdog import run_watcher
from plants_tagger.util.logger import configure_root_logger


configure_root_logger()
logging.getLogger(__name__).info('Creating App.')
app = create_app()

if __name__ == "__main__":
    photo_dir_watcher_thread = threading.Thread(name="Photo Directory Watchdog", target=run_watcher)
    photo_dir_watcher_thread.setDaemon(True)
    photo_dir_watcher_thread.start()
    app.run(debug=True)
    logging.getLogger(__name__).info('Starting App serving UWSGI.')
