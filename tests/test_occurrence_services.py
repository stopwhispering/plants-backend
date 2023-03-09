from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import plants as plants_package
from plants.modules.biodiversity.taxonomy_occurence_images import TaxonOccurencesLoader

if TYPE_CHECKING:
    from plants.modules.taxon.models import Taxon
    from plants.modules.taxon.taxon_dal import TaxonDAL


@pytest.mark.asyncio()
async def test_taxon_occurrence_loader(
    # test_db: AsyncSession,
    # plant_valid,
    # plant_dal: PlantDAL,
    # event_dal: EventDAL,
    taxon_dal: TaxonDAL,
    taxon_in_db: Taxon,
) -> None:
    # Scrape occurrences for taxon "Haworthia coarctata"
    loader = TaxonOccurencesLoader(taxon_dal=taxon_dal)
    assert taxon_in_db.gbif_id is not None
    await loader.scrape_occurrences_for_taxon(gbif_id=taxon_in_db.gbif_id)

    # Check if occurrences were added to the taxon in the db
    taxon_id = taxon_in_db.id
    taxon_dal.expire_all()
    taxon = await taxon_dal.by_id(taxon_id)
    assert len(taxon.occurrence_images) > 0
    occurrence_image = taxon.occurrence_images[0]
    assert occurrence_image.gbif_id == taxon.gbif_id

    # Check if image thumbnail was saved to file system
    folder_content = (
        plants_package.settings.paths.path_generated_thumbnails_taxon.iterdir()
    )
    file_names = [f.name for f in folder_content]

    # the thumbnail filenames contain at least the occurrence_id, img_no, and gbif_id
    assert next(
        f
        for f in file_names
        if str(occurrence_image.occurrence_id) in f
        and str(occurrence_image.img_no) in f
        and str(occurrence_image.gbif_id) in f
    )
