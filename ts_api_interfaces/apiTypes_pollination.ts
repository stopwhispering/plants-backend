
export type BFlorescenceStatus = "inflorescence_appeared" | "flowering" | "finished";
export type FlowerColorDifferentiation = "top_bottom" | "ovary_mouth" | "uniform";
export type StigmaPosition = "exserted" | "mouth" | "inserted" | "deeply_inserted";
export type BFloweringState = "inflorescence_growing" | "flowering" | "seeds_ripening" | "not_flowering";
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";
export type PollenType = "fresh" | "frozen" | "unknown";
export type PollinationStatus = "attempt" | "seed_capsule" | "seed" | "germinated" | "unknown" | "self_pollinated";

export interface BActiveFlorescence {
  id: number;
  plant_id: number;
  plant_name: string;
  florescence_status: BFlorescenceStatus;
  inflorescence_appearance_date?: string;
  comment?: string;
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
  available_colors_rgb: string[];
}
export interface BFloweringPeriodState {
  month: string;
  flowering_state: BFloweringState;
}
export interface BOngoingPollination {
  seed_capsule_plant_id: number;
  seed_capsule_plant_name: string;
  pollen_donor_plant_id: number;
  pollen_donor_plant_name: string;
  pollination_timestamp?: string;
  pollen_type: string;
  location?: string;
  location_text: string;
  label_color_rgb: string;
  id: number;
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
  action: string;
  message?: BMessage;
  activeFlorescenceCollection: BActiveFlorescence[];
}
export interface BResultsFlowerHistory {
  action: string;
  message: BMessage;
  plants: BPlantFlowerHistory[];
  months: string[];
}
export interface BResultsOngoingPollinations {
  action: string;
  message?: BMessage;
  ongoingPollinationCollection: BOngoingPollination[];
}
export interface BResultsPlantsForNewFlorescence {
  plantsForNewFlorescenceCollection: BPlantForNewFlorescence[];
}
export interface BResultsPollenContainers {
  pollenContainerCollection: FBPollenContainer[];
  plantsWithoutPollenContainerCollection: BPlantWithoutPollenContainer[];
}
export interface FBPollenContainer {
  plant_id: number;
  plant_name: string;
  genus?: string;
  count_stored_pollen_containers: number;
}
export interface BResultsPotentialPollenDonors {
  action: string;
  message?: BMessage;
  potentialPollenDonorCollection: BPotentialPollenDonor[];
}
export interface BResultsRetrainingPollinationToSeedsModel {
  mean_f1_score: number;
  model: string;
}
export interface BResultsSettings {
  colors: string[];
}
export interface FRequestEditedFlorescence {
  id: number;
  plant_id: number;
  florescence_status: BFlorescenceStatus;
  inflorescence_appearance_date?: string;
  comment?: string;
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
export interface FRequestEditedPollination {
  id: number;
  seed_capsule_plant_id: number;
  pollen_donor_plant_id: number;
  pollination_timestamp?: string;
  pollen_type: PollenType;
  location?: string;
  label_color_rgb: string;
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
export interface FRequestNewFlorescence {
  plant_id: number;
  florescence_status: BFlorescenceStatus;
  inflorescence_appearance_date?: string;
  comment?: string;
}
export interface FRequestNewPollination {
  florescenceId: number;
  seedCapsulePlantId: number;
  pollenDonorPlantId: number;
  pollenType: PollenType;
  pollinationTimestamp: string;
  labelColorRgb: string;
  location: string;
}
export interface FRequestPollenContainers {
  pollenContainerCollection: FBPollenContainer[];
}