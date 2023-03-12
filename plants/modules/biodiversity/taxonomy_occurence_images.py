from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import TYPE_CHECKING

import aiohttp
from dateutil.parser import isoparse
from pydantic.error_wrappers import ValidationError
from pygbif import occurrences as occ_api
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from plants import local_config, settings
from plants.modules.image.util import generate_thumbnail
from plants.modules.taxon.models import (
    TaxonOccurrenceImage,
    TaxonToOccurrenceAssociation,
)
from plants.modules.taxon.schemas import TaxonOccurrenceImageRead
from plants.shared.message_services import throw_exception

if TYPE_CHECKING:
    from datetime import datetime

    from plants.modules.biodiversity.api_typedefs import (
        GbifMediaDict,
        GbifOccurrenceResultDict,
        GbifOccurrenceResultResponse,
    )
    from plants.modules.taxon.taxon_dal import TaxonDAL

logger = logging.getLogger(__name__)


# @dataclass
# class ImageMetadata:
#     occurrence_id: int
#     gbif_id: int
#     scientific_name: str
#     basis_of_record: str
#     verbatim_locality: str | None
#     photographed_at: datetime | None
#     creator_identifier: str
#     publisher_dataset: str
#     href: str
#     references: str | None
#     img_no: int | None = None
#     filename_thumbnail: str | None = None


class OccurrenceNotCompleteError(Exception):
    """Raised when a GBIF occurrence object is not complete or can't be parsed for any
    other reason."""


class ImageMetadata:
    def __init__(
        self, occ: GbifOccurrenceResultDict, m: GbifMediaDict, gbif_id: int, img_no: int
    ):
        self.occurrence_id: int = occ["key"]
        self.gbif_id: int = gbif_id
        self.img_no: int = img_no
        self.scientific_name: str = occ["scientificName"]
        self.basis_of_record: str = occ["basisOfRecord"]
        self.verbatim_locality: str | None = self._parse_verbatim_locality(occ)
        self.photographed_at: datetime | None = self._parse_photographed_at(
            m=m, occ=occ
        )
        self.creator_identifier: str = self._parse_creator_identifier(m=m, occ=occ)
        self.publisher_dataset: str = self._parse_publisher_dataset(m=m, occ=occ)
        self.href = self._parse_href(m=m)
        self.references: str | None = self._parse_references(occ=occ)
        self.filename_thumbnail = self.generate_filename_thumbnail(
            gbif_id=gbif_id, img_no=img_no, occurrence_id=self.occurrence_id
        )

    @staticmethod
    def _parse_references(occ: GbifOccurrenceResultDict) -> str | None:
        if (references := occ.get("references")) and references[:4].lower() == "http":
            return occ["references"]
        return None

    @staticmethod
    def _parse_href(m: GbifMediaDict) -> str:
        """Get the photo_file href."""
        if m.get("references") and (
            "jpg" in m["references"].lower() or "jpeg" in m["references"].lower()
        ):
            return m["references"]
        if m.get("identifier"):
            return m["identifier"]
        raise OccurrenceNotCompleteError('No "references" or "identifier" found')

    @staticmethod
    def _parse_verbatim_locality(occ: GbifOccurrenceResultDict) -> str | None:
        verbatim_locality = occ.get("verbatimLocality") or occ.get("locality")
        if verbatim_locality:
            if occ.get("countryCode") and occ.get("stateProvince"):
                geo = f" ({occ['stateProvince']}, {occ['countryCode']})"
            elif occ.get("countryCode"):
                geo = f" ({occ['countryCode']})"
            elif occ.get("stateProvince"):
                geo = f" ({occ['stateProvince']})"
            else:
                geo = ""
            verbatim_locality += geo
        return verbatim_locality

    @staticmethod
    def _parse_photographed_at(
        occ: GbifOccurrenceResultDict, m: GbifMediaDict
    ) -> datetime | None:
        if "created" not in m and "eventDate" not in occ:
            # happens very rarely, so wen can skip entries with unknown date
            raise OccurrenceNotCompleteError('No "created" or "eventDate" found')
        created_ = m.get("created") or occ.get("eventDate")
        return isoparse(created_) if created_ else None

    @staticmethod
    def _parse_creator_identifier(
        occ: GbifOccurrenceResultDict, m: GbifMediaDict
    ) -> str:
        return (
            m.get("identifiedBy")
            or m.get("creator")
            or occ.get("recordedBy")
            or "Unknown Creator"
        )

    @staticmethod
    def _parse_publisher_dataset(
        occ: GbifOccurrenceResultDict, m: GbifMediaDict
    ) -> str:
        return (
            occ.get("publisher")
            or m.get("publisher")
            or occ.get("institutionCode")
            or occ.get("rightsHolder")
            or occ.get("datasetName")
            or occ.get("collectionCode")
            or "Unknown Publisher"
        )

    @staticmethod
    def generate_filename_thumbnail(
        gbif_id: int, img_no: int, occurrence_id: int
    ) -> str:
        return (
            f"{gbif_id}_{occurrence_id}_{img_no}."
            f"{settings.images.size_thumbnail_image_taxon[0]}_"
            f"{settings.images.size_thumbnail_image_taxon[1]}.jpg"
        )


class TaxonOccurencesLoader:
    def __init__(self, taxon_dal: TaxonDAL):
        self.taxon_dal = taxon_dal

    @staticmethod
    def _get_image_metadata(
        occ: GbifOccurrenceResultDict, m: GbifMediaDict, gbif_id: int, img_no: int
    ) -> ImageMetadata | None:
        try:
            image_metadata = ImageMetadata(occ=occ, m=m, gbif_id=gbif_id, img_no=img_no)
        except (KeyError, OccurrenceNotCompleteError) as err:
            # in rare cases, essential properties are missing
            logger.warning(str(err))
            return None

        return image_metadata

    @staticmethod
    async def _download_and_generate_thumbnail(info: ImageMetadata) -> bool:
        if settings.paths.path_generated_thumbnails_taxon.joinpath(
            info.filename_thumbnail
        ).is_file():
            logger.debug(f"File already downloaded. Skipping download - {info.href}")
            return True

        logger.debug(f"Downloading... {str(info.href)}")
        async with aiohttp.ClientSession() as session:
            async with session.get(info.href) as response:
                if response.status >= 300:
                    logger.warning(f"Download failed: {info.href}")
                    return False
                payload = await response.read()
        image_bytes_io = BytesIO(payload)

        try:
            path_thumbnail = generate_thumbnail(
                image=image_bytes_io,
                size=settings.images.size_thumbnail_image_taxon,
                path_thumbnail=settings.paths.path_generated_thumbnails_taxon,
                filename_thumb=info.filename_thumbnail,
                ignore_missing_image_files=(
                    local_config.log_settings.ignore_missing_image_files
                ),
            )
        except OSError as err:
            logger.warning(f"Could not load as image: {info.href} ({str(err)}")
            return False

        info.filename_thumbnail = info.filename_thumbnail
        logger.debug(f"Saved {path_thumbnail}")

        return True

    async def _download_and_save_thumbnail(
        self,
        occ: GbifOccurrenceResultDict,
        gbif_id: int,
        img_no: int,
        gbif_media_dict: GbifMediaDict,
    ) -> ImageMetadata | None:
        image_metadata = self._get_image_metadata(occ, gbif_media_dict, gbif_id, img_no)
        if not image_metadata:
            return None

        if not await self._download_and_generate_thumbnail(image_metadata):
            return None

        # validate (don't convert as this would convert datetime to str
        try:
            TaxonOccurrenceImageRead(**image_metadata.__dict__)
        except ValidationError as err:
            throw_exception(str(err))
            return None

        return image_metadata

    async def _treat_occurences(
        self, occs: list[GbifOccurrenceResultDict], gbif_id: int
    ) -> list[ImageMetadata]:
        image_dicts: list[ImageMetadata] = []
        for occ in occs:
            if len(image_dicts) >= local_config.max_images_per_taxon:
                break

            # some entries are not parseable
            media = [m for m in occ["media"] if "format" in m]
            gbif_media_dict: GbifMediaDict
            tasks = []
            for img_no, gbif_media_dict in enumerate(media, 1):
                tasks.append(
                    self._download_and_save_thumbnail(
                        occ=occ,
                        gbif_id=gbif_id,
                        img_no=img_no,
                        gbif_media_dict=gbif_media_dict,
                    )
                )
            results = await asyncio.gather(*tasks)
            image_dicts.extend([r for r in results if r])

        return image_dicts

    async def _save_to_db(self, image_dicts: list[ImageMetadata], gbif_id: int) -> None:
        # cleanup existing entries for taxon
        await self.taxon_dal.delete_taxon_to_occurrence_associations_by_gbif_id(gbif_id)
        await self.taxon_dal.delete_taxon_occurrence_image_by_gbif_id(gbif_id)

        # insert new entries
        new_occurrence_images: list[TaxonOccurrenceImage] = []
        new_taxon_occ_links: list[TaxonToOccurrenceAssociation] = []
        for img in image_dicts:
            record = TaxonOccurrenceImage(**img.__dict__)
            new_occurrence_images.append(record)

            # assign occurrence image to each taxon with that gbif id (usually only one)
            # taxa = db.query(Taxon).filter(Taxon.gbif_id == gbif_id).all()
            taxa = await self.taxon_dal.by_gbif_id(gbif_id)
            taxon_ids = [t.id for t in taxa]
            record_associations = [
                TaxonToOccurrenceAssociation(
                    taxon_id=taxon_id,
                    occurrence_id=img.occurrence_id,
                    img_no=img.img_no,
                    gbif_id=gbif_id,
                )
                for taxon_id in taxon_ids
            ]
            new_taxon_occ_links.extend(record_associations)

        try:
            if new_occurrence_images:
                await self.taxon_dal.create_taxon_occurrence_images(
                    new_occurrence_images
                )
            if new_taxon_occ_links:
                await self.taxon_dal.create_taxon_to_occurrence_associations(
                    new_taxon_occ_links
                )
        except IntegrityError:
            logger.exception("IntegrityError while saving occurrence images.")

    async def scrape_occurrences_for_taxon(
        self, gbif_id: int
    ) -> list[TaxonOccurrenceImage]:
        logger.info(f"Searching occurrence images for  {gbif_id}.")

        # the gbif api is blocking, so we better run it in a threadpool
        occ_search: GbifOccurrenceResultResponse = await run_in_threadpool(
            occ_api.search, taxonKey=gbif_id, mediaType="StillImage"
        )
        if not occ_search["results"]:
            logger.info(f"nothing found for {gbif_id}")
            return []

        logger.info(
            f'gbif_id: {str(gbif_id)} --> {occ_search["results"][0]["scientificName"]} '
        )
        occurrences = [
            o
            for o in occ_search["results"]
            if o.get("basisOfRecord") != "PRESERVED_SPECIMEN" and o.get("countryCode")
        ]

        # get photo_file information & save thumbnail
        image_dicts: list[ImageMetadata] = await self._treat_occurences(
            occurrences, gbif_id
        )

        # save information to database
        logger.info(
            f"Saving/Updating {len(image_dicts)} occurrence images to database."
        )

        await self._save_to_db(image_dicts, gbif_id)

        self.taxon_dal.expire_all()
        taxa = await self.taxon_dal.by_gbif_id(gbif_id)
        # we assigned to each taxon with that gbif id, here we just use the first
        taxon = taxa[0]
        return taxon.occurrence_images
