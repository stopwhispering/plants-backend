
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";
export type FBShapeTop = "square" | "round" | "oval" | "hexagonal";
export type FBShapeSide = "very flat" | "flat" | "high" | "very high";

export interface BPResultsUpdateCreateSoil {
  action?: string;
  message: BMessage;
  soil: SoilRead;
}
export interface SoilRead {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
}
export interface BResultsEventResource {
  action?: string;
  message: BMessage;
  events: EventRead[];
}
export interface EventRead {
  plant_id: number;
  date: string;
  event_notes?: string;
  images?: FBImageAssignedToEvent[];
  id: number;
  observation?: ObservationRead;
  soil?: SoilRead;
  pot?: PotRead;
}
export interface FBImageAssignedToEvent {
  id: number;
  filename: string;
}
export interface ObservationRead {
  diseases?: string;
  stem_max_diameter?: number;
  height?: number;
  observation_notes?: string;
  id: number;
}
export interface PotRead {
  material: string;
  shape_top: FBShapeTop;
  shape_side: FBShapeSide;
  diameter_width: number;
  id: number;
}
export interface BResultsSoilsResource {
  SoilsCollection: SoilWithCountRead[];
}
export interface SoilWithCountRead {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
  plants_count: number;
}
export interface EventCreateUpdate {
  plant_id: number;
  date: string;
  event_notes?: string;
  images?: FBImageAssignedToEvent[];
  id?: number;
  observation?: ObservationCreateUpdate;
  soil?: SoilUpdate;
  pot?: PotCreateUpdate;
}
export interface ObservationCreateUpdate {
  diseases?: string;
  stem_max_diameter?: number;
  height?: number;
  observation_notes?: string;
  id?: number;
}
export interface SoilUpdate {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
}
export interface PotCreateUpdate {
  material: string;
  shape_top: FBShapeTop;
  shape_side: FBShapeSide;
  diameter_width: number;
  id?: number;
}
export interface FImageDelete {
  id: number;
  filename: string;
}
export interface FImagesToDelete {
  images: FImageDelete[];
}
export interface FRequestCreateOrUpdateEvent {
  plants_to_events: {
    [k: string]: EventCreateUpdate[];
  };
}
export interface ObservationBase {
  diseases?: string;
  stem_max_diameter?: number;
  height?: number;
  observation_notes?: string;
}
export interface PotBase {
  material: string;
  shape_top: FBShapeTop;
  shape_side: FBShapeSide;
  diameter_width: number;
}
export interface SoilBase {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
}
export interface SoilCreate {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
}
