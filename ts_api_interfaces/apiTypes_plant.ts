
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
export type TagState = "None" | "Indication01" | "Success" | "Information" | "Error" | "Warning";
export type FBMajorResource = "PlantResource" | "ImageResource" | "TaxonResource" | "EventResource";

export interface BPlantsRenameRequest {
  plant_id: number;
  old_plant_name: string;
  new_plant_name: string;
}
export interface BResultsPlantCloned {
  action?: string;
  message: BMessage;
  plant: PlantRead;
}
export interface PlantRead {
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
  parent_plant?: ShortPlant;
  parent_plant_pollen?: ShortPlant;
  plant_notes?: string;
  filename_previewimage?: string;
  tags: FBPlantTag[];
  id: number;
  taxon_authors?: string;
  botanical_name?: string;
  full_botanical_html_name?: string;
  created_at: string;
  last_update?: string;
  descendant_plants_all: ShortPlant[];
  sibling_plants: ShortPlant[];
  same_taxon_plants: ShortPlant[];
  current_soil?: PlantCurrentSoil;
  latest_image?: PlantLatestImage;
}
export interface ShortPlant {
  id: number;
  plant_name: string;
  active: boolean;
}
export interface FBPlantTag {
  id?: number;
  state: TagState;
  text: string;
  last_update?: string;
  plant_id: number;
}
export interface PlantCurrentSoil {
  soil_name: string;
  date: string;
}
export interface PlantLatestImage {
  path: string;
  date: string;
}
export interface BResultsPlants {
  action?: string;
  message: BMessage;
  PlantsCollection: PlantRead[];
}
export interface BResultsPlantsUpdate {
  action?: string;
  message: BMessage;
  resource: FBMajorResource;
  plants: PlantRead[];
}
export interface BResultsProposeSubsequentPlantName {
  original_plant_name: string;
  subsequent_plant_name: string;
}
export interface PlantCreateUpdate {
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
  parent_plant?: ShortPlant;
  parent_plant_pollen?: ShortPlant;
  plant_notes?: string;
  filename_previewimage?: string;
  tags: FBPlantTag[];
  id?: number;
}
export interface PlantBase {
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
  parent_plant?: ShortPlant;
  parent_plant_pollen?: ShortPlant;
  plant_notes?: string;
  filename_previewimage?: string;
  tags: FBPlantTag[];
}
