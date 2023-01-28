import logging
from threading import Thread

from pykew import powo
from sqlalchemy.orm import Session

from plants.modules.biodiversity.taxonomy_lookup_gbif_id import GBIFIdentifierLookup
from plants.modules.biodiversity.taxonomy_name_formatter import BotanicalNameInput, create_formatted_botanical_name
from plants.modules.biodiversity.taxonomy_occurence_images import TaxonOccurencesLoader
from plants.shared.message__services import throw_exception
from plants.modules.taxon.models import Taxon, Distribution
from plants.modules.image.models import ImageToTaxonAssociation, Image
from plants.modules.taxon.schemas import FTaxon, FTaxonImage, FNewTaxon

logger = logging.getLogger(__name__)


def _create_names(new_taxon: FNewTaxon) -> tuple[str, str]:
    """
    create a simple and a html-formatted botanical name
    """
    botanical_name_input = BotanicalNameInput(
        rank=new_taxon.rank,
        genus=new_taxon.genus,
        species=new_taxon.species,
        infraspecies=new_taxon.infraspecies,
        hybrid=new_taxon.hybrid,
        hybridgenus=new_taxon.hybridgenus,
        is_custom=new_taxon.is_custom,
        cultivar=new_taxon.cultivar,
        affinis=new_taxon.affinis,
        custom_rank=new_taxon.custom_rank,
        custom_infraspecies=new_taxon.custom_infraspecies,
        authors=new_taxon.authors,
        name_published_in_year=new_taxon.namePublishedInYear,
        custom_suffix=new_taxon.custom_suffix,
    )
    full_html_name = create_formatted_botanical_name(botanical_attributes=botanical_name_input,
                                                     include_publication=True,
                                                     html=True)
    name = create_formatted_botanical_name(botanical_attributes=botanical_name_input,
                                           include_publication=False,
                                           html=False)
    return name, full_html_name


def _retrieve_locations(lsid: str):
    powo_lookup = powo.lookup(lsid, include=['distribution'])
    locations: list[Distribution] = []

    # collect native and introduced distribution into one list
    dist = []
    if distribution := powo_lookup.get('distribution'):
        distribution: dict
        if natives := distribution.get('natives'):
            dist.extend(natives)
        if introduced := distribution.get('introduced'):
            dist.extend(introduced)

    if not dist:
        logger.info(f'No locations found for {lsid}.')
    else:
        for area in dist:
            record = Distribution(name=area.get('name'),
                                  establishment=area.get('establishment'),
                                  feature_id=area.get('featureId'),
                                  tdwg_code=area.get('tdwgCode'),
                                  tdwg_level=area.get('tdwgLevel')
                                  )
            locations.append(record)
    return locations


def save_new_taxon(new_taxon: FNewTaxon, db: Session) -> Taxon:

    name, full_html_name = _create_names(new_taxon)

    if new_taxon.is_custom:
        assert ((new_taxon.custom_rank and new_taxon.custom_infraspecies)
                or new_taxon.custom_suffix or new_taxon.cultivar or new_taxon.affinis)
        locations = []
        gbif_id = None
    else:
        assert not new_taxon.custom_rank
        assert not new_taxon.custom_infraspecies
        assert not new_taxon.custom_suffix
        assert not new_taxon.cultivar
        assert not new_taxon.affinis
        locations = _retrieve_locations(new_taxon.lsid)

        gbif_identifier_lookup = GBIFIdentifierLookup()
        gbif_id = gbif_identifier_lookup.lookup(taxon_name=name, lsid=new_taxon.lsid)

    existing = Taxon.get_taxon_by_taxon_name(taxon_name=name, db=db, raise_exception=False)
    if existing:
        throw_exception(f'Taxon with name {name} already exists.')

    taxon = Taxon(
        name=name,
        full_html_name=full_html_name,
        gbif_id=gbif_id,
        distribution=locations,

        # attributes from ipni/powo
        rank=new_taxon.rank,
        # phylum=new_taxon.phylum,
        family=new_taxon.family,
        genus=new_taxon.genus,
        species=new_taxon.species,
        infraspecies=new_taxon.infraspecies,
        lsid=new_taxon.lsid,
        taxonomic_status=new_taxon.taxonomic_status,
        synonym=new_taxon.synonym,
        authors=new_taxon.authors,
        name_published_in_year=new_taxon.namePublishedInYear,
        basionym=new_taxon.basionym,
        hybrid=new_taxon.hybrid,
        hybridgenus=new_taxon.hybridgenus,
        synonyms_concat=new_taxon.synonyms_concat,
        distribution_concat=new_taxon.distribution_concat,

        # custom attributes
        is_custom=new_taxon.is_custom,
        custom_rank=new_taxon.custom_rank,
        custom_infraspecies=new_taxon.custom_infraspecies,
        cultivar=new_taxon.cultivar,
        affinis=new_taxon.affinis,
        custom_suffix=new_taxon.custom_suffix,
        custom_notes='',
    )
    db.add(taxon)

    # lookup ocurrences & image URLs at GBIF and generate thumbnails for found image URLs
    loader = TaxonOccurencesLoader(db=db)
    thread = Thread(target=loader.scrape_occurrences_for_taxon, args=[gbif_id])
    logger.info(f'Starting thread to load occurences for gbif_id {gbif_id}')
    thread.start()

    return taxon


def modify_taxon(taxon_modified: FTaxon, db: Session):
    taxon: Taxon = db.query(Taxon).filter(Taxon.id == taxon_modified.id).first()
    if not taxon:
        logger.error(f'Taxon not found: {taxon.name}. Saving canceled.')
        throw_exception(f'Taxon not found: {taxon.name}. Saving canceled.')

    taxon.custom_notes = taxon_modified.custom_notes

    # changes to images attached to the taxon
    image: FTaxonImage
    filenames_saved = ([image.filename for image in taxon_modified.images]
                       if taxon_modified.images else [])
    for image_obj in taxon.images:
        image_obj: Image
        if image_obj.filename not in filenames_saved:
            # don't delete photo_file object, but only the association
            # (photo_file might be assigned to other events)
            link: ImageToTaxonAssociation
            db.delete([link for link in taxon.image_to_taxon_associations if
                       link.image.relative_path == image_obj.relative_path][0])

    # newly assigned images
    if taxon_modified.images:
        for image in taxon_modified.images:
            # image_obj = db.query(Image).filter(Image.relative_path == image.relative_path.as_posix()).first()
            image_obj = Image.get_image_by_id(id_=image.id, db=db)
            # if not image_obj:
            # if not Image.exists(filename=image.filename, db=db):
            #     # not assigned to any event, yet
            #     raise ValueError(f'Image not in db: {image.relative_path.as_posix()}')

            # update link table including the photo_file description
            current_taxon_to_image_link = [t for t in taxon.image_to_taxon_associations if t.image == image_obj]

            # insert link
            if not current_taxon_to_image_link:
                link = ImageToTaxonAssociation(image_id=image_obj.id,
                                               taxon_id=taxon.id,
                                               description=image.description)
                db.add(link)
                logger.info(f'Image {image_obj.relative_path} assigned to taxon {taxon.name}')

            # update description
            elif current_taxon_to_image_link[0].description != image.description:
                current_taxon_to_image_link[0].description = image.description
                logger.info(f'Update description of link between image {image_obj.relative_path} and taxon'
                            f' {taxon.name}')