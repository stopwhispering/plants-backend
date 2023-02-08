from typing import List, Dict, Optional
import requests
from pydantic.error_wrappers import ValidationError
from pygbif import occurrences as occ_api
from io import BytesIO
import logging
import dateutil
from sqlalchemy.exc import IntegrityError

from plants import local_config, settings
from plants.modules.plant.taxon_dal import TaxonDAL
from plants.shared.message_services import throw_exception
from plants.modules.taxon.models import TaxonOccurrenceImage, TaxonToOccurrenceAssociation
from plants.modules.image.util import generate_thumbnail
from plants.modules.taxon.schemas import BTaxonOccurrenceImage

logger = logging.getLogger(__name__)


class TaxonOccurencesLoader:
    def __init__(self, taxon_dal: TaxonDAL):
        self.taxon_dal = taxon_dal

    @staticmethod
    def _get_image_metadata(occ: dict, m: dict, gbif_id: int) -> Optional[dict]:
        if 'created' not in m and 'eventDate' not in occ:
            # happens very rarely, so wen can skip entries with unknown date
            return

        try:
            d = {'occurrence_id': occ['key'],
                 'gbif_id': gbif_id,  # occ['taxonKey'],
                 'scientific_name': occ['scientificName'],  # redundant, but show as additional info
                 'basis_of_record': occ['basisOfRecord'],
                 'verbatim_locality': occ.get('verbatimLocality') or occ.get('locality'),
                 'date': dateutil.parser.isoparse(m.get('created') or occ.get('eventDate')),  # noqa
                 'creator_identifier': m.get('identifiedBy') or m.get('creator') or occ.get('recordedBy'),
                 'publisher_dataset': occ.get('publisher') or m.get('publisher') or occ.get(
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
        filename = (f"{info['gbif_id']}_{info['occurrence_id']}_{info['img_no']}."
                    f"{settings.images.size_thumbnail_image_taxon[0]}_"
                    f"{settings.images.size_thumbnail_image_taxon[1]}.jpg")

        if settings.paths.path_generated_thumbnails_taxon.joinpath(filename).is_file():
            logger.debug(f'File already downloaded. Skipping download - {info["href"]}')
            return filename

        logger.info(f'Downloading... {info["href"]}')
        result = requests.get(info["href"])
        if not (200 <= result.status_code < 300):
            logger.warning(f'Download failed: {info["href"]}')
            return

        image_bytes_io = BytesIO(result.content)
        try:
            path_thumbnail = generate_thumbnail(
                image=image_bytes_io,
                size=settings.images.size_thumbnail_image_taxon,
                path_thumbnail=settings.paths.path_generated_thumbnails_taxon,
                filename_thumb=filename,
                ignore_missing_image_files=local_config.log_settings.ignore_missing_image_files)
        except OSError as err:
            logger.warning(f"Could not load as image: {info['href']} ({str(err)}")
            return

        info['filename_thumbnail'] = filename
        logger.debug(f'Saved {path_thumbnail}')

        return filename

    def _treat_occurences(self, occs: List, gbif_id: int) -> List[Dict]:
        image_dicts = []
        for occ in occs:
            if len(image_dicts) >= local_config.max_images_per_taxon:
                break

            media = [m for m in occ['media'] if 'format' in m]  # some entries are not parseable
            for j, m in enumerate(media, 1):
                if len(image_dicts) >= local_config.max_images_per_taxon:
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
                        BTaxonOccurrenceImage(**d).dict()
                    except ValidationError as err:
                        throw_exception(str(err))
                        # logger.warning(str(err))
                        continue

                    # saving will happen later
                    image_dicts.append(d)

        return image_dicts

    async def _save_to_db(self, image_dicts: List[Dict], gbif_id: int):
        # cleanup existing entries for taxon
        await self.taxon_dal.delete_taxon_to_occurrence_associations_by_gbif_id(gbif_id)
        await self.taxon_dal.delete_taxon_occurrence_image_by_gbif_id(gbif_id)
        # db.query(TaxonToOccurrenceAssociation).filter(TaxonToOccurrenceAssociation.gbif_id == gbif_id).delete()
        # db.query(TaxonOccurrenceImage).filter(TaxonOccurrenceImage.gbif_id == gbif_id).delete()

        # insert new entries
        new_occurrence_images: list[TaxonOccurrenceImage] = []
        new_taxon_occ_links: list[TaxonToOccurrenceAssociation] = []
        for img in image_dicts:
            record = TaxonOccurrenceImage(**img)
            new_occurrence_images.append(record)

            # assign occurrence image to each taxon with that gbif id (usually only one)
            # taxa = db.query(Taxon).filter(Taxon.gbif_id == gbif_id).all()
            taxa = await self.taxon_dal.by_gbif_id(gbif_id)
            taxon_ids = [t.id for t in taxa]
            record_associations = [TaxonToOccurrenceAssociation(taxon_id=taxon_id,
                                                                occurrence_id=img['occurrence_id'],
                                                                img_no=img['img_no'],
                                                                gbif_id=gbif_id) for taxon_id in taxon_ids]
            new_taxon_occ_links.extend(record_associations)

        try:
            if new_occurrence_images:
                await self.taxon_dal.create_taxon_occurrence_images(new_occurrence_images)
            if new_taxon_occ_links:
                await self.taxon_dal.create_taxon_to_occurrence_associations(new_taxon_occ_links)
        except IntegrityError as err:
            logger.error(str(err))
            print(err)

    async def scrape_occurrences_for_taxon(self, gbif_id: int) -> list[TaxonOccurrenceImage]:
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
        await self._save_to_db(image_dicts, gbif_id)

        taxa = await self.taxon_dal.by_gbif_id(gbif_id)
        taxon = taxa[0]  # we assigned to each taxon with that gbif id, here we just use the first
        # taxon: Taxon = self.db.query(Taxon).filter(Taxon.gbif_id == gbif_id).first()
        return taxon.occurrence_images
