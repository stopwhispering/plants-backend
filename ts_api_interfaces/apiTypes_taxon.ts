
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";
export type FBRank = "gen." | "spec." | "subsp." | "var." | "forma";

export interface BCreatedTaxonResponse {
  action: string;
  message: BMessage;
  new_taxon: BTaxon;
}
export interface BTaxon {
  id: number;
  name: string;
  is_custom: boolean;
  species?: string;
  infraspecies?: string;
  cultivar?: string;
  affinis?: string;
  genus: string;
  family: string;
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
export interface BKewSearchResultEntry {
  id?: number;
  in_db: boolean;
  count: number;
  count_inactive: number;
  synonym: boolean;
  authors: string;
  family: string;
  name: string;
  rank: string;
  taxonomic_status: string;
  lsid: string;
  genus: string;
  species?: string;
  infraspecies?: string;
  is_custom: boolean;
  custom_rank?: FBRank;
  custom_infraspecies?: string;
  cultivar?: string;
  affinis?: string;
  custom_suffix?: string;
  hybrid: boolean;
  hybridgenus: boolean;
  name_published_in_year?: number;
  basionym?: string;
  synonyms_concat?: string;
  distribution_concat?: string;
}
export interface BResultsFetchTaxonImages {
  action: string;
  message: BMessage;
  occurrence_images: BTaxonOccurrenceImage[];
}
export interface BResultsGetBotanicalName {
  full_html_name: string;
  name: string;
}
export interface BResultsGetTaxon {
  action: string;
  message: BMessage;
  taxon: BTaxon;
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
export interface FBotanicalAttributes {
  rank: string;
  genus: string;
  species?: string;
  infraspecies?: string;
  hybrid: boolean;
  hybridgenus: boolean;
  authors?: string;
  name_published_in_year?: number;
  is_custom: boolean;
  cultivar?: string;
  affinis?: string;
  custom_rank?: string;
  custom_infraspecies?: string;
  custom_suffix?: string;
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
  species?: string;
  genus: string;
  family: string;
  infraspecies?: string;
  cultivar?: string;
  affinis?: string;
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
  distribution?: FBDistribution;
  images?: FTaxonImage[];
}
export interface FTaxonImage {
  id: number;
  filename: string;
  description?: string;
}
export interface FNewTaxon {
  id?: number;
  rank: string;
  family: string;
  genus: string;
  species?: string;
  infraspecies?: string;
  lsid: string;
  taxonomic_status: string;
  synonym: boolean;
  authors: string;
  name_published_in_year?: number;
  basionym?: string;
  hybrid: boolean;
  hybridgenus: boolean;
  synonyms_concat?: string;
  distribution_concat?: string;
  is_custom: boolean;
  custom_rank?: FBRank;
  custom_infraspecies?: string;
  cultivar?: string;
  affinis?: string;
  custom_suffix?: string;
}
export interface FRetrieveTaxonDetailsRequest {
  lsid?: string;
  hasCustomName: boolean;
  taxon_id?: number;
  nameInclAddition: string;
  plant_id: number;
  source: string;
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
