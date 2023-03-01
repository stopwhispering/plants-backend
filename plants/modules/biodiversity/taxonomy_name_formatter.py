from dataclasses import dataclass

from plants.modules.taxon.enums import FBRank
from plants.modules.taxon.models import Taxon


@dataclass
class PartOfBotanicalName:
    name: str
    italics: bool


@dataclass
class BotanicalNameInput:
    rank: str
    genus: str
    species: str | None
    infraspecies: str | None
    hybrid: bool
    hybridgenus: bool
    is_custom: bool
    cultivar: str | None
    affinis: str | None
    custom_rank: str | None
    custom_infraspecies: str | None
    authors: str | None
    name_published_in_year: int | None
    custom_suffix: str | None


def _disassemble_taxon_name(  # noqa: C901 PLR0912
    botanical_name_input: BotanicalNameInput,
) -> list[PartOfBotanicalName]:
    genus_name = (
        botanical_name_input.genus
        if not botanical_name_input.hybridgenus
        else "× " + botanical_name_input.genus
    )
    parts: list[PartOfBotanicalName] = [
        PartOfBotanicalName(name=genus_name, italics=True)
    ]

    if botanical_name_input.species:
        species = (
            botanical_name_input.species
            if not botanical_name_input.hybrid or botanical_name_input.hybridgenus
            else "× " + botanical_name_input.species
        )
        parts.append(PartOfBotanicalName(name=species, italics=True))

    if botanical_name_input.infraspecies:
        if botanical_name_input.rank == FBRank.SUBSPECIES.value:
            parts.append(PartOfBotanicalName(name="ssp.", italics=False))
            parts.append(
                PartOfBotanicalName(
                    name=botanical_name_input.infraspecies, italics=True
                )
            )
        elif botanical_name_input.rank == FBRank.VARIETY.value:
            parts.append(PartOfBotanicalName(name="var.", italics=False))
            parts.append(
                PartOfBotanicalName(
                    name=botanical_name_input.infraspecies, italics=True
                )
            )
        elif botanical_name_input.rank == FBRank.FORMA.value:
            parts.append(PartOfBotanicalName(name="f.", italics=False))
            parts.append(
                PartOfBotanicalName(
                    name=botanical_name_input.infraspecies, italics=True
                )
            )
        else:
            raise ValueError(f"Unexpected rank: {botanical_name_input.rank}")

    if botanical_name_input.custom_infraspecies:
        if botanical_name_input.custom_rank == FBRank.SUBSPECIES.value:
            parts.append(PartOfBotanicalName(name="ssp.", italics=False))
            parts.append(
                PartOfBotanicalName(
                    name=botanical_name_input.custom_infraspecies, italics=True
                )
            )
        elif botanical_name_input.custom_rank == FBRank.VARIETY.value:
            parts.append(PartOfBotanicalName(name="var.", italics=False))
            parts.append(
                PartOfBotanicalName(
                    name=botanical_name_input.custom_infraspecies, italics=True
                )
            )
        elif botanical_name_input.custom_rank == FBRank.FORMA.value:
            parts.append(PartOfBotanicalName(name="f.", italics=False))
            parts.append(
                PartOfBotanicalName(
                    name=botanical_name_input.custom_infraspecies, italics=True
                )
            )
        else:
            raise ValueError(
                f"Unexpected custom rank: {botanical_name_input.custom_rank}"
            )

    if botanical_name_input.cultivar:
        parts.append(PartOfBotanicalName(name="cv.", italics=False))
        parts.append(
            PartOfBotanicalName(
                name="'" + botanical_name_input.cultivar + "'", italics=False
            )
        )

    if botanical_name_input.affinis:
        parts.append(PartOfBotanicalName(name="aff.", italics=False))
        parts.append(
            PartOfBotanicalName(name=botanical_name_input.affinis, italics=False)
        )

    if botanical_name_input.custom_suffix:
        parts.append(
            PartOfBotanicalName(name=botanical_name_input.custom_suffix, italics=False)
        )

    return parts


def _create_formatted_name(parts: list[PartOfBotanicalName], *, html: bool) -> str:
    parts_str: list[str] = []
    italics_active = False
    for p in parts:
        if html and p.italics and not italics_active:
            parts_str.append(f"<em>{p.name}")
            italics_active = True
        elif html and not p.italics and italics_active:
            parts_str.append(f"</em>{p.name}")
            italics_active = False
        else:
            parts_str.append(p.name)
    if html and italics_active:
        parts_str.append("</em>")

    return " ".join(parts_str)


def _create_publication_parts(
    botanical_name_input: BotanicalNameInput,
) -> list[PartOfBotanicalName]:
    if not botanical_name_input.authors:
        return []
    publication_parts = [
        PartOfBotanicalName(name=botanical_name_input.authors, italics=False)
    ]
    if botanical_name_input.name_published_in_year:
        publication_parts.append(
            PartOfBotanicalName(
                name=" (" + str(botanical_name_input.name_published_in_year) + ")",
                italics=False,
            )
        )
    return publication_parts


def create_formatted_botanical_name(
    botanical_attributes: Taxon | BotanicalNameInput,
    *,
    include_publication: bool,
    html: bool,
) -> str:
    """Create a html-formatted botanical name for supplied taxon."""
    if isinstance(botanical_attributes, Taxon):
        botanical_name_input = BotanicalNameInput(
            rank=botanical_attributes.rank,
            genus=botanical_attributes.genus,
            species=botanical_attributes.species,
            infraspecies=botanical_attributes.infraspecies,
            hybrid=botanical_attributes.hybrid,
            hybridgenus=botanical_attributes.hybridgenus,
            is_custom=botanical_attributes.is_custom,
            cultivar=botanical_attributes.cultivar,
            affinis=botanical_attributes.affinis,
            custom_rank=botanical_attributes.custom_rank,
            custom_infraspecies=botanical_attributes.custom_infraspecies,
            authors=botanical_attributes.authors,
            name_published_in_year=botanical_attributes.name_published_in_year,
            custom_suffix=botanical_attributes.custom_suffix,
        )
    elif isinstance(botanical_attributes, BotanicalNameInput):
        botanical_name_input = botanical_attributes
    else:
        raise TypeError("Either Taxon or Botanical Name Input must be provided")

    name_parts: list[PartOfBotanicalName] = _disassemble_taxon_name(
        botanical_name_input
    )
    publication_parts: list[PartOfBotanicalName] = _create_publication_parts(
        botanical_name_input
    )

    if include_publication:
        return _create_formatted_name(parts=name_parts + publication_parts, html=html)
    return _create_formatted_name(parts=name_parts, html=html)
