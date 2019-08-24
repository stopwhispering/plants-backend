from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import logging

import plants_tagger.config_local
from plants_tagger.config_local import folder_root_original_images, path_uploaded_photos_original
from plants_tagger.models.files import photo_directory, lock_photo_directory, FOLDER_ROOT
import plants_tagger.models.files

dt_last_change = None
logger = logging.getLogger(__name__)


class PhotoFolderFileEventsHandler(FileSystemEventHandler):

    def __init__(self, observer):
        super().__init__()
        self.observer = observer

    def _order_refresh(self, event):
        """there are usually multiple changes within short time. therefore wait some seconds and check if
        there were any further changes; wait until no further changes, then re-generate the photo files directory"""

        logger.info(f'Watchdog event: {event.event_type}, path: {event.src_path}. Waiting some seconds for further '
                    f'events.')
        queue = self.observer.event_queue
        finished = False
        while not finished:
            time.sleep(10)
            if not queue.qsize():
                finished = True
            else:
                logger.info(f'Found {queue.qsize()} further events. Waiting, again.')
                while queue.qsize():
                    _ = queue.get()

        with lock_photo_directory:
            if plants_tagger.models.files.photo_directory:
                plants_tagger.models.files.photo_directory.refresh_directory(
                    plants_tagger.config_local.path_frontend_temp)

    def on_created(self, event):
        self._order_refresh(event)

    def on_moved(self, event):
        self._order_refresh(event)

    def on_deleted(self, event):
        self._order_refresh(event)


def run_watcher():
    """run in thread from wsgi.py"""
    observer = Observer()
    handler = PhotoFolderFileEventsHandler(observer)
    observer.schedule(handler, folder_root_original_images, recursive=True)
    observer.schedule(handler, path_uploaded_photos_original, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(15)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
