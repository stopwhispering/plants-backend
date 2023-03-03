from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from plants.modules.biodiversity.taxonomy_occurence_images import TaxonOccurencesLoader

if TYPE_CHECKING:
    # from plants.modules.taxon.models import TaxonOccurrenceImage
    from plants.modules.taxon.taxon_dal import TaxonDAL


@pytest.mark.asyncio()
async def test_taxon_occurrence_loader(
    # test_db: AsyncSession,
    # plant_valid,
    # plant_dal: PlantDAL,
    # event_dal: EventDAL,
    taxon_dal: TaxonDAL,
) -> None:
    TaxonOccurencesLoader(taxon_dal=taxon_dal)
    # loader.scrape_occurrences_for_taxon(gbif_id=9549498)  # H. coarctata
    # images: list[TaxonOccurrenceImage]
    # await loader.scrape_occurrences_for_taxon(gbif_id=9549498)  # H. coarctata

    # todo : test...
    #
    #
    # test_db.add(plant_valid)
    # await test_db.commit()
    # plant_valid = await plant_dal.by_id(plant_valid.id)
    #
    # await deep_clone_plant(
    #     plant_valid,
    #     plant_name_clone="Aloe Vera Clone",
    #     plant_dal=plant_dal,
    #     event_dal=event_dal,
    #     # property_dal=property_dal
    # )
    # await test_db.commit()
