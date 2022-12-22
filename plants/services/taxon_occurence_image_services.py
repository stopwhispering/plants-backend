from typing import List, Dict, Optional
import requests
from pydantic.error_wrappers import ValidationError
from pygbif import occurrences as occ_api
from io import BytesIO
import logging
import dateutil
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from plants import config
from plants.util.ui_utils import throw_exception
from plants.models.taxon_models import TaxonOccurrenceImage, Taxon
from plants.util.image_utils import generate_thumbnail
from plants.validation.taxon_validation import PTaxonOccurrenceImage

logger = logging.getLogger(__name__)


def get_occurrence_thumbnail_filename(gbif_id: int, occurrence_id: int, img_no: int, size_x: int, size_y: int) -> str:
    filename = f"{gbif_id}_{occurrence_id}_{img_no}." \
               f"{size_x}_{size_y}.jpg"
    return filename

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
                 'date':               dateutil.parser.isoparse(m.get('created') or occ.get('eventDate')),  # noqa
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

            # get the photo_file href
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
        # filename = f"{info['gbif_id']}_{info['occurrence_id']}_{info['img_no']}." \
        #            f"{size_x}_{size_y}.jpg"
        filename = get_occurrence_thumbnail_filename(gbif_id=info['gbif_id'],
                                                     occurrence_id=info['occurrence_id'],
                                                     img_no=info['img_no'],
                                                     size_x=config.size_thumbnail_image_taxon[0],
                                                     size_y=config.size_thumbnail_image_taxon[1])
        href = info['href']

        if config.path_generated_thumbnails_taxon.joinpath(filename).is_file():
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
                                                size=config.size_thumbnail_image_taxon,
                                                path_thumbnail=config.path_generated_thumbnails_taxon,
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
            if len(image_dicts) >= config.max_images_per_taxon:
                break

            media = [m for m in occ['media'] if 'format' in m]  # some entries are not parseable
            for j, m in enumerate(media, 1):
                if len(image_dicts) >= config.max_images_per_taxon:
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
    def _save_to_db(image_dicts: List[Dict], gbif_id: int, db: Session):
        # cleanup existing entries for taxon
        db.query(TaxonOccurrenceImage).filter(TaxonOccurrenceImage.gbif_id == gbif_id).delete()

        # insert new entries
        new_list = []
        for img in image_dicts:
            record = TaxonOccurrenceImage(**img)
            new_list.append(record)

        if new_list:
            try:
                db.add_all(new_list)
                db.commit()  # saves changes in existing records, too
            except IntegrityError as err:
                logger.error(str(err))
                print(err)

    def scrape_occurrences_for_taxon(self, gbif_id: int, db: Session) -> List:
        logger.info(f'Searching occurrence immages for  {gbif_id}.')
        occ_search = occ_api.search(taxonKey=gbif_id, mediaType='StillImage')
        if not occ_search['results']:
            logger.info(f'nothing found for {gbif_id}')
            return []

        logger.info(f'gbif_id: {str(gbif_id)} --> {occ_search["results"][0]["scientificName"]} ')
        occurrences = [o for o in occ_search['results'] if o.get('basisOfRecord') != 'PRESERVED_SPECIMEN'
                       and o.get('countryCode')]

        # get photo_file information & save thumbnail
        image_dicts = self._treat_occurences(occurrences, gbif_id)

        # save information to database
        logger.info(f'Saving/Updating {len(image_dicts)} occurrence images to database.')
        self._save_to_db(image_dicts, gbif_id, db)

        taxon: Taxon = db.query(Taxon).filter(Taxon.gbif_id == gbif_id).first()
        occurrence_images = [o.as_dict() for o in taxon.occurrence_images]

        return occurrence_images
