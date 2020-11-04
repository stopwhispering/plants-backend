from typing import List, Dict, Optional
import os
import requests
from flask_2_ui5_py import throw_exception
from pydantic.error_wrappers import ValidationError
from pygbif import occurrences as occ_api
from io import BytesIO
import logging
import dateutil
from sqlalchemy.exc import IntegrityError

from plants_tagger.config import size_tumbnail_image_taxon
from plants_tagger.config_local import MAX_IMAGES_PER_TAXON
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.taxon_models import TaxonOccurrenceImage
from plants_tagger.services.os_paths import PATH_GENERATED_THUMBNAILS_TAXON
from plants_tagger.util.image_utils import generate_thumbnail
from plants_tagger.validation.taxon_validation import PTaxonOccurrenceImage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # todo remove


class TaxonOccurencesLoader:

    @staticmethod
    def _get_image_metadata(occ: dict, m: dict, gbif_id: int) -> Optional[dict]:
        if 'created' not in m and 'eventDate' not in occ:
            # happens very rarely, so wen can skip entries with unknown date
            return

        try:
            d = {'occurrence_id':      occ['key'],
                 'gbif_id':            gbif_id,  # occ['taxonKey'],
                 'scientific_name':    occ['scientificName'],  # redundant, but show as additional info
                 'basis_of_record':    occ['basisOfRecord'],
                 'verbatim_locality':  occ.get('verbatimLocality') or occ.get('locality'),
                 'date':               dateutil.parser.isoparse(m.get('created') or occ.get('eventDate')),
                 'creator_identifier': m.get('identifiedBy') or m.get('creator') or occ.get('recordedBy'),
                 'publisher_dataset':  occ.get('publisher') or m.get('publisher') or occ.get(
                         'institutionCode') or occ.get('rightsHolder') or occ.get('datasetName') or occ.get(
                         'collectionCode'),
                 }

            # combine some infos
            if occ.get('countryCode') and occ.get('stateProvince'):
                geo = f" ({occ['stateProvince']}, {occ['countryCode']})"
            elif occ.get('countryCode'):
                geo = f" ({occ['countryCode']})"
            elif occ.get('stateProvince'):
                geo = f" ({occ['stateProvince']})"
            else:
                geo = ''
            if d['verbatim_locality']:
                d['verbatim_locality'] += geo

            # some fields requiring validation
            if (references := occ.get('references')) and references[:4].lower() == 'http':
                d['references'] = occ['references']
            else:
                d['references'] = None

            # get the photo href
            if m.get('references') and ('jpg' in m['references'].lower() or 'jpeg' in m['references'].lower()):
                d['href'] = m['references']
            elif m.get('identifier') and ('jpg' in m['identifier'].lower() or 'jpeg' in m['identifier'].lower()):
                d['href'] = m['identifier']
            elif m.get('identifier'):
                d['href'] = m['identifier']
            else:
                return

        # in rare cases, essential properties are missing
        except KeyError as err:
            logger.warning(str(err))
            return

        return d

    @staticmethod
    def _download_and_generate_thumbnail(info: Dict) -> Optional[str]:
        filename = f"{info['gbif_id']}_{info['occurrence_id']}_{info['img_no']}." \
                   f"{size_tumbnail_image_taxon[0]}_{size_tumbnail_image_taxon[1]}.jpg"
        href = info['href']

        if os.path.isfile(os.path.join(PATH_GENERATED_THUMBNAILS_TAXON, filename)):
            logger.debug(f'File already downloaded. Skipping download - {href}')
            return filename

        logger.info(f'Downloading... {href}')
        result = requests.get(href)
        if not (200 <= result.status_code < 300):
            logger.warning(f'Download failed: {href}')
            return

        image_bytes_io = BytesIO(result.content)
        try:
            path_thumbnail = generate_thumbnail(image=image_bytes_io,
                                                size=size_tumbnail_image_taxon,
                                                path_thumbnail=PATH_GENERATED_THUMBNAILS_TAXON,
                                                filename_thumb=filename)
        except OSError as err:
            logger.warning(f"Could not load as image: {href} ({str(err)}")
            return

        info['filename_thumbnail'] = filename
        logger.debug(f'Saved {path_thumbnail}')

        return filename

    def _treat_occurences(self, occs: List, gbif_id: int) -> List[Dict]:
        image_dicts = []
        for occ in occs:
            if len(image_dicts) >= MAX_IMAGES_PER_TAXON:
                break

            media = [m for m in occ['media'] if 'format' in m]  # some entries are not parseable
            for j, m in enumerate(media, 1):
                if len(image_dicts) >= MAX_IMAGES_PER_TAXON:
                    break

                d = self._get_image_metadata(occ, m, gbif_id)
                if d:
                    d['img_no'] = j

                    if filename_thumbnail := self._download_and_generate_thumbnail(d):
                        d['filename_thumbnail'] = filename_thumbnail
                    else:
                        continue

                    # validate (don't convert as this would validate datetime to str
                    try:
                        PTaxonOccurrenceImage(**d).dict()
                    except ValidationError as err:
                        throw_exception(str(err))
                        # logger.warning(str(err))
                        continue

                    # saving will happen later
                    image_dicts.append(d)

        return image_dicts

    @staticmethod
    def _save_to_db(image_dicts: List[Dict], gbif_id: int):
        # cleanup existing entries for taxon
        get_sql_session().query(TaxonOccurrenceImage).filter(TaxonOccurrenceImage.gbif_id == gbif_id).delete()

        # insert new entries
        new_list = []
        for img in image_dicts:
            record = TaxonOccurrenceImage(**img)
            new_list.append(record)

        if new_list:
            try:
                get_sql_session().add_all(new_list)
                get_sql_session().commit()  # saves changes in existing records, too
            except IntegrityError as err:
                logger.error(str(err))
                print(err)

    def scrape_occurrences_for_taxon(self, gbif_id: int) -> List:
        occ_search = occ_api.search(taxonKey=gbif_id, mediaType='StillImage')
        if not occ_search['results']:
            logger.info(f'nothing found for {gbif_id}')
            return []

        logger.info(f'gbif_id: {str(gbif_id)} --> {occ_search["results"][0]["scientificName"]} ')
        occurrences = [o for o in occ_search['results'] if o.get('basisOfRecord') != 'PRESERVED_SPECIMEN'
                       and o.get('countryCode')]

        # get image information & save thumbnail
        image_dicts = self._treat_occurences(occurrences, gbif_id)

        # save information to database
        logger.info(f'Saving/Updating {len(image_dicts)} occurrence images to database.')
        self._save_to_db(image_dicts, gbif_id)

        return image_dicts
