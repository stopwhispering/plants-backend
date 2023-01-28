
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";
export type FBPropagationType =
  | "seed (collected)"
  | "offset"
  | "acquired as plant"
  | "bulbil"
  | "head cutting"
  | "leaf cutting"
  | "seed (purchased)"
  | "unknown"
  | "";
export type FBCancellationReason =
  | "Winter Damage"
  | "Dried Out"
  | "Mould"
  | "Mites"
  | "Other Insects"
  | "Abandonment"
  | "Gift"
  | "Sale"
  | "Others";
export type FBTagState = "None" | "Indication01" | "Success" | "Information" | "Error" | "Warning";
export type FBMajorResource =
  | "PlantResource"
  | "ImageResource"
  | "TaxonResource"
  | "EventResource"
  | "PlantPropertyResource"
  | "TaxonPropertyResource";

export interface BPlant {
  id: number;
  plant_name: string;
  field_number?: string;
  geographic_origin?: string;
  nursery_source?: string;
  propagation_type?: FBPropagationType;
  active: boolean;
  cancellation_reason?: FBCancellationReason;
  cancellation_date?: string;
  generation_notes?: string;
  taxon_id?: number;
  taxon_authors?: string;
  botanical_name?: string;
  full_botanical_html_name?: string;
  parent_plant?: FBAssociatedPlantExtractForPlant;
  parent_plant_pollen?: FBAssociatedPlantExtractForPlant;
  plant_notes?: string;
  filename_previewimage?: string;
  last_update?: string;
  descendant_plants_all: FBAssociatedPlantExtractForPlant[];
  sibling_plants: FBAssociatedPlantExtractForPlant[];
  same_taxon_plants: FBAssociatedPlantExtractForPlant[];
  current_soil?: FBPlantCurrentSoil;
  latest_image?: FBPlantLatestImage;
  tags: FBPlantTag[];
}
export interface FBAssociatedPlantExtractForPlant {
  id: number;
  plant_name: string;
  active: boolean;
}
export interface FBPlantCurrentSoil {
  soil_name: string;
  date: string;
}
export interface FBPlantLatestImage {
  path: string;
  date: string;
}
export interface FBPlantTag {
  id?: number;
  state: FBTagState;
  text: string;
  last_update?: string;
  plant_id: number;
}
export interface BPlantsRenameRequest {
  OldPlantName: string;
  NewPlantName: string;
}
export interface BResultsPlantCloned {
  action: string;
  message: BMessage;
  plant: BPlant;
}
export interface BResultsPlants {
  action: string;
  message: BMessage;
  PlantsCollection: BPlant[];
}
export interface BResultsPlantsUpdate {
  action: string;
  resource: FBMajorResource;
  message: BMessage;
  plants: BPlant[];
}
export interface BResultsProposeSubsequentPlantName {
  original_plant_name: string;
  subsequent_plant_name: string;
}
export interface FPlant {
  id?: number;
  plant_name: string;
  field_number?: string;
  geographic_origin?: string;
  nursery_source?: string;
  propagation_type?: FBPropagationType;
  active: boolean;
  cancellation_reason?: FBCancellationReason;
  cancellation_date?: string;
  generation_notes?: string;
  taxon_id?: number;
  taxon_authors?: string;
  botanical_name?: string;
  full_botanical_html_name?: string;
  parent_plant?: FBAssociatedPlantExtractForPlant;
  parent_plant_pollen?: FBAssociatedPlantExtractForPlant;
  plant_notes?: string;
  filename_previewimage?: string;
  last_update?: string;
  descendant_plants_all: FBAssociatedPlantExtractForPlant[];
  sibling_plants: FBAssociatedPlantExtractForPlant[];
  same_taxon_plants: FBAssociatedPlantExtractForPlant[];
  current_soil?: FBPlantCurrentSoil;
  latest_image?: FBPlantLatestImage;
  tags: FBPlantTag[];
}
export interface FPlantsDeleteRequest {
  plant_id: number;
}
export interface FPlantsUpdateRequest {
  PlantsCollection: FPlant[];
}
