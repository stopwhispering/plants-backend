
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface BKewSearchResultEntry {
  source: string;
  id?: number;
  count: number;
  count_inactive: number;
  is_custom: boolean;
  synonym: boolean;
  authors: string;
  family: string;
  name: string;
  rank: string;
  fqId?: string;
  powo_id?: string;
  genus: string;
  species?: string;
  namePublishedInYear: string;
  phylum?: string;
  synonyms_concat?: string;
  distribution_concat?: string;
}
export interface BResultsFetchTaxonImages {
  action: string;
  resource: string;
  message: BMessage;
  occurrenceImages?: FBTaxonOccurrenceImage[];
}
export interface FBTaxonOccurrenceImage {
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
export interface BResultsGetTaxa {
  action: string;
  resource: string;
  message?: BMessage;
  TaxaDict: {
    [k: string]: FBTaxon;
  };
}
export interface FBTaxon {
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
  fq_id?: string;
  authors?: string;
  basionym?: string;
  synonyms_concat?: string;
  distribution_concat?: string;
  hybrid: boolean;
  hybridgenus: boolean;
  gbif_id?: string;
  powo_id?: string;
  custom_notes?: string;
  ipni_id_short: string;
  distribution?: FBDistribution;
  images?: FBTaxonImage[];
  occurrenceImages?: FBTaxonOccurrenceImage[];
}
export interface FBDistribution {
  native: string[];
  introduced: string[];
}
export interface FBTaxonImage {
  id?: number;
  filename: string;
  description?: string;
}
export interface BResultsSaveTaxonRequest {
  action: string;
  resource: string;
  message: BMessage;
  botanical_name: string;
  taxon_data: FBTaxon;
}
export interface BResultsTaxonInfoRequest {
  action: string;
  resource: string;
  message: BMessage;
  ResultsCollection: BKewSearchResultEntry[];
}
export interface FAssignTaxonRequest {
  fqId?: string;
  hasCustomName: boolean;
  id?: number;
  nameInclAddition: string;
  plant_id: number;
  source: string;
}
export interface FFetchTaxonImages {
  gbif_id: number;
}
export interface FModifiedTaxa {
  ModifiedTaxaCollection: FBTaxon[];
}
export interface FTaxonInfoRequest {
  includeKew: boolean;
  searchForGenus: boolean;
  species: string;
}
