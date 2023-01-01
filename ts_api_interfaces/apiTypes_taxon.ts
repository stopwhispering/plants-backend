
export type BSearchResultSource =
  | "Local DB"
  | "Plants of the World"
  | "International Plant Names Index + Plants of the World";
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface BKewSearchResultEntry {
  source: BSearchResultSource;
  id?: number;
  count: number;
  count_inactive: number;
  is_custom: boolean;
  synonym?: boolean;
  authors: string;
  family: string;
  name: string;
  rank: string;
  lsid: string;
  genus: string;
  species?: string;
  namePublishedInYear?: string;
  phylum?: string;
  synonyms_concat?: string;
  distribution_concat?: string;
}
export interface BResultsFetchTaxonImages {
  action: string;
  message: BMessage;
  occurrence_images: BTaxonOccurrenceImage[];
}
export interface BTaxonOccurrenceImage {
  occurrence_id: number;
  img_no: number;
  gbif_id: number;
  scientific_name: string;
  basis_of_record: string;
  verbatim_locality?: string;
  date: string;
  creator_identifier: string;
  publisher_dataset?: string;
  references?: string;
  href: string;
  filename_thumbnail: string;
}
export interface BResultsGetTaxon {
  action: string;
  message: BMessage;
  taxon: BTaxon;
}
export interface BTaxon {
  id: number;
  name: string;
  is_custom: boolean;
  subsp?: string;
  species?: string;
  subgen?: string;
  genus: string;
  family: string;
  phylum?: string;
  kingdom?: string;
  rank: string;
  taxonomic_status?: string;
  name_published_in_year?: number;
  synonym: boolean;
  lsid?: string;
  authors?: string;
  basionym?: string;
  synonyms_concat?: string;
  distribution_concat?: string;
  hybrid: boolean;
  hybridgenus: boolean;
  gbif_id?: number;
  custom_notes?: string;
  distribution: FBDistribution;
  images: BTaxonImage[];
  occurrence_images: BTaxonOccurrenceImage[];
}
export interface FBDistribution {
  native: string[];
  introduced: string[];
}
export interface BTaxonImage {
  id: number;
  filename: string;
  description?: string;
}
export interface BResultsRetrieveTaxonDetailsRequest {
  action: string;
  message: BMessage;
  botanical_name: string;
  taxon_data: BTaxon;
}
export interface BResultsTaxonInfoRequest {
  action: string;
  message: BMessage;
  ResultsCollection: BKewSearchResultEntry[];
}
export interface FAssignTaxonRequest {
  lsid?: string;
  hasCustomName: boolean;
  taxon_id?: number;
  nameInclAddition: string;
  plant_id: number;
  source: string;
}
export interface FFetchTaxonOccurrenceImagesRequest {
  gbif_id: number;
}
export interface FModifiedTaxa {
  ModifiedTaxaCollection: FTaxon[];
}
export interface FTaxon {
  id: number;
  name: string;
  is_custom: boolean;
  subsp?: string;
  species?: string;
  subgen?: string;
  genus: string;
  family: string;
  phylum?: string;
  kingdom?: string;
  rank: string;
  taxonomic_status?: string;
  name_published_in_year?: number;
  synonym: boolean;
  lsid?: string;
  authors?: string;
  basionym?: string;
  synonyms_concat?: string;
  distribution_concat?: string;
  hybrid: boolean;
  hybridgenus: boolean;
  gbif_id?: string;
  custom_notes?: string;
  distribution?: FBDistribution;
  images?: FTaxonImage[];
}
export interface FTaxonImage {
  id: number;
  filename: string;
  description?: string;
}
export interface FTaxonInfoRequest {
  include_external_apis: boolean;
  taxon_name_pattern: string;
  search_for_genus_not_species: boolean;
}
export interface FTaxonOccurrenceImage {
  occurrence_id: number;
  img_no: number;
  gbif_id: number;
  scientific_name: string;
  basis_of_record: string;
  verbatim_locality?: string;
  date: string;
  creator_identifier: string;
  publisher_dataset?: string;
  references?: string;
  href: string;
  filename_thumbnail: string;
}
