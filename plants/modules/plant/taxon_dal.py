from sqlalchemy import select, delete

from plants.exceptions import TaxonNotFound, ImageNotAssignedToTaxon
from plants.modules.image.models import ImageToTaxonAssociation
from plants.modules.taxon.models import Taxon, TaxonToOccurrenceAssociation, TaxonOccurrenceImage
from plants.modules.taxon.schemas import FBRank
from plants.shared.base_dal import BaseDAL


class TaxonDAL(BaseDAL):
    def __init__(self, session):
        super().__init__(session)

    def by_id(self, taxon_id: int) -> Taxon:
        query = (select(Taxon)
                 .where(Taxon.id == taxon_id)  # noqa
                 .limit(1))
        taxon: Taxon = (self.session.scalars(query)).first()  # noqa
        if not taxon:
            raise TaxonNotFound(taxon_id)
        return taxon

    def by_gbif_id(self, gbif_id: int) -> list[Taxon]:
        query = (select(Taxon)
                 .where(Taxon.gbif_id == gbif_id)  # noqa
                 )
        taxa: list[Taxon] = (self.session.scalars(query)).all()  # noqa
        return taxa

    def get_taxa_by_name_pattern(self, taxon_name_pattern: str, rank: FBRank = None) -> list[Taxon]:

        query = (select(Taxon)
                 .where(Taxon.name.ilike(taxon_name_pattern))  # ilike ~ case-insensitive like
                 )
        if rank:
            query = query.where(Taxon.rank == rank.value)  # noqa
        taxa: list[Taxon] = (self.session.scalars(query)).all()  # noqa
        return taxa

    def get_taxon_occurrence_image_by_filter(self, criteria: dict) -> list[TaxonOccurrenceImage]:
        query = select(TaxonOccurrenceImage)
        for key, value in criteria.items():
            if key == 'gbif_id':
                value: int
                query = query.where(TaxonOccurrenceImage.gbif_id == value)
            elif key == 'occurrence_id':
                value: int
                query = query.where(TaxonOccurrenceImage.occurrence_id == value)
            elif key == 'img_no':
                value: int
                query = query.where(TaxonOccurrenceImage.img_no == value)
            else:
                raise NotImplemented(f'Invalid filter key: {key}')

        images: list[TaxonOccurrenceImage] = (self.session.scalars(query)).all()  # noqa
        return images

    # def get_taxon_to_occurrence_associations_by_gbif_id(self, gbif_id: int) -> list[TaxonToOccurrenceAssociation]:
    #     query = (select(TaxonToOccurrenceAssociation)
    #              .where(TaxonToOccurrenceAssociation.gbif_id == gbif_id)  # noqa
    #              )
    #     links: list[TaxonToOccurrenceAssociation] = (self.session.scalars(query)).all()  # noqa
    #     return links

    def create_taxon_to_occurrence_associations(self, links: list[TaxonToOccurrenceAssociation]):
        self.session.add_all(links)
        self.session.flush()

    def create_taxon_occurrence_images(self, occurrence_images:  list[TaxonOccurrenceImage]):
        self.session.add_all(occurrence_images)
        self.session.flush()

    def create_image_to_taxon_association(self, image_to_taxon_association:  list[ImageToTaxonAssociation]):
        self.session.add(image_to_taxon_association)
        self.session.flush()

    def delete_taxon_to_occurrence_associations_by_gbif_id(self, gbif_id: int):
        query = (delete(TaxonToOccurrenceAssociation)
                 .where(TaxonToOccurrenceAssociation.gbif_id == gbif_id)
                 )
        self.session.execute(query)
        self.session.flush()

    def delete_taxon_occurrence_image_by_gbif_id(self, gbif_id: int):
        query = (delete(TaxonOccurrenceImage)
                 .where(TaxonOccurrenceImage.gbif_id == gbif_id)
                 )
        self.session.execute(query)
        self.session.flush()

    def delete_image_association_from_taxon(self, taxon: Taxon, link: ImageToTaxonAssociation):
        if link not in taxon.image_to_taxon_associations:
            raise ImageNotAssignedToTaxon(taxon.id, link.image_id)
        taxon.image_to_taxon_associations.remove(link)

        self.session.delete(link)
        self.session.flush()

    def exists(self, taxon_name: str) -> bool:
        query = (select(Taxon)
                 .where(Taxon.name == taxon_name)  # noqa
                 .limit(1))
        taxon: Taxon = (self.session.scalars(query)).first()  # noqa
        return taxon is not None

    def create(self, taxon: Taxon):
        self.session.add(taxon)
        self.session.flush()

    def update(self, taxon: Taxon, updates: dict):
        if 'custom_notes' in updates:
            taxon.custom_notes = updates['custom_notes']

        self.session.flush()
