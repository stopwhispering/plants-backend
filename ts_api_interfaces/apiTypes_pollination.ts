
export type BFloweringState = "inflorescence_growing" | "flowering" | "seeds_ripening" | "not_flowering";
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";
export type FlorescenceStatus = "inflorescence_appeared" | "flowering" | "finished" | "aborted";
export type FlowerColorDifferentiation = "top_bottom" | "ovary_mouth" | "uniform";
export type StigmaPosition = "exserted" | "mouth" | "inserted" | "deeply_inserted";
export type PollenType = "fresh" | "frozen" | "unknown";
export type PollinationStatus = "attempt" | "seed_capsule" | "seed" | "germinated" | "unknown" | "self_pollinated";

export interface BFloweringPeriodState {
  month: string;
  flowering_state: BFloweringState;
}
export interface BPlantFlowerHistory {
  plant_id: number;
  plant_name: string;
  periods: BFloweringPeriodState[];
}
export interface BPlantForNewFlorescence {
  plant_id: number;
  plant_name: string;
  genus?: string;
}
export interface BPlantWithoutPollenContainer {
  plant_id: number;
  plant_name: string;
  genus?: string;
}
export interface BPollinationAttempt {
  reverse: boolean;
  pollination_status: string;
  pollination_at?: string;
  harvest_at?: string;
  germination_rate?: number;
  ongoing: boolean;
}
export interface BPollinationResultingPlant {
  plant_id: number;
  plant_name: string;
  reverse: boolean;
}
export interface BPollinationStatus {
  key: string;
  text: string;
}
export interface BPotentialPollenDonor {
  plant_id: number;
  plant_name: string;
  pollen_type: string;
  count_stored_pollen_containers?: number;
  already_ongoing_attempt: boolean;
  probability_pollination_to_seed?: number;
  pollination_attempts: BPollinationAttempt[];
  resulting_plants: BPollinationResultingPlant[];
}
export interface BResultsActiveFlorescences {
  action?: string;
  message: BMessage;
  activeFlorescenceCollection: FlorescenceRead[];
}
export interface FlorescenceRead {
  plant_id: number;
  florescence_status: FlorescenceStatus;
  inflorescence_appearance_date?: string;
  comment?: string;
  id: number;
  plant_name: string;
  available_colors_rgb: string[];
  branches_count?: number;
  flowers_count?: number;
  perianth_length?: number;
  perianth_diameter?: number;
  flower_color?: string;
  flower_color_second?: string;
  flower_colors_differentiation?: FlowerColorDifferentiation;
  stigma_position?: StigmaPosition;
  first_flower_opening_date?: string;
  last_flower_closing_date?: string;
}
export interface BResultsFlowerHistory {
  action?: string;
  message: BMessage;
  plants: BPlantFlowerHistory[];
  months: string[];
}
export interface BResultsOngoingPollinations {
  action?: string;
  message: BMessage;
  ongoingPollinationCollection: PollinationRead[];
}
export interface PollinationRead {
  seed_capsule_plant_id: number;
  pollen_donor_plant_id: number;
  pollen_type: PollenType;
  pollination_timestamp: string;
  label_color_rgb: string;
  location: string;
  count?: number;
  id: number;
  seed_capsule_plant_name: string;
  pollen_donor_plant_name: string;
  location_text: string;
  pollination_status: string;
  ongoing: boolean;
  harvest_date?: string;
  seed_capsule_length?: number;
  seed_capsule_width?: number;
  seed_length?: number;
  seed_width?: number;
  seed_count?: number;
  seed_capsule_description?: string;
  seed_description?: string;
  days_until_first_germination?: number;
  first_seeds_sown?: number;
  first_seeds_germinated?: number;
  germination_rate?: number;
}
export interface BResultsPlantsForNewFlorescence {
  plantsForNewFlorescenceCollection: BPlantForNewFlorescence[];
}
export interface BResultsPollenContainers {
  pollenContainerCollection: PollenContainerRead[];
  plantsWithoutPollenContainerCollection: BPlantWithoutPollenContainer[];
}
export interface PollenContainerRead {
  plant_id: number;
  plant_name: string;
  genus?: string;
  count_stored_pollen_containers: number;
}
export interface BResultsPotentialPollenDonors {
  action?: string;
  message: BMessage;
  potentialPollenDonorCollection: BPotentialPollenDonor[];
}
export interface BResultsRetrainingPollinationToSeedsModel {
  mean_f1_score: number;
  model: string;
}
export interface BResultsSettings {
  colors: string[];
}
export interface PollenContainerCreateUpdate {
  plant_id: number;
  plant_name: string;
  genus?: string;
  count_stored_pollen_containers: number;
}
export interface FlorescenceBase {
  plant_id: number;
  florescence_status: FlorescenceStatus;
  inflorescence_appearance_date?: string;
  comment?: string;
}
export interface FlorescenceCreate {
  plant_id: number;
  florescence_status: FlorescenceStatus;
  inflorescence_appearance_date?: string;
  comment?: string;
}
export interface FlorescenceUpdate {
  plant_id: number;
  florescence_status: FlorescenceStatus;
  inflorescence_appearance_date?: string;
  comment?: string;
  id: number;
  branches_count?: number;
  flowers_count?: number;
  perianth_length?: number;
  perianth_diameter?: number;
  flower_color?: string;
  flower_color_second?: string;
  flower_colors_differentiation?: FlowerColorDifferentiation;
  stigma_position?: StigmaPosition;
  first_flower_opening_date?: string;
  last_flower_closing_date?: string;
}
export interface PollenContainerBase {
  plant_id: number;
  plant_name: string;
  genus?: string;
  count_stored_pollen_containers: number;
}
export interface PollinationBase {
  seed_capsule_plant_id: number;
  pollen_donor_plant_id: number;
  pollen_type: PollenType;
  pollination_timestamp: string;
  label_color_rgb: string;
  location: string;
  count: number;
}
export interface PollinationCreate {
  seed_capsule_plant_id: number;
  pollen_donor_plant_id: number;
  pollen_type: PollenType;
  pollination_timestamp: string;
  label_color_rgb: string;
  location: string;
  count: number;
  florescenceId: number;
}
export interface PollinationUpdate {
  seed_capsule_plant_id: number;
  pollen_donor_plant_id: number;
  pollen_type: PollenType;
  pollination_timestamp: string;
  label_color_rgb: string;
  location: string;
  count: number;
  id: number;
  pollination_status: PollinationStatus;
  ongoing: boolean;
  harvest_date?: string;
  seed_capsule_length?: number;
  seed_capsule_width?: number;
  seed_length?: number;
  seed_width?: number;
  seed_count?: number;
  seed_capsule_description?: string;
  seed_description?: string;
  days_until_first_germination?: number;
  first_seeds_sown?: number;
  first_seeds_germinated?: number;
}
