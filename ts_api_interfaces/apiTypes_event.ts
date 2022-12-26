
export type FBShapeTop = "square" | "round" | "oval" | "hexagonal";
export type FBShapeSide = "very flat" | "flat" | "high" | "very high";
export type BEvents = BEvent[];
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface BEvent {
  id: number;
  plant_id: number;
  date: string;
  event_notes?: string;
  observation?: BObservation;
  soil?: BSoil;
  pot?: BPot;
  images?: FBImageAssignedToEvent[];
}
export interface BObservation {
  id?: number;
  diseases?: string;
  stem_max_diameter?: number;
  height?: number;
  observation_notes?: string;
}
export interface BSoil {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
}
export interface BPot {
  id?: number;
  material: string;
  shape_top: FBShapeTop;
  shape_side: FBShapeSide;
  diameter_width: number;
}
export interface FBImageAssignedToEvent {
  id: number;
  filename: string;
}
export interface BPResultsUpdateCreateSoil {
  soil: BSoil;
  message: BMessage;
}
export interface BResultsEventResource {
  events: BEvents;
  message: BMessage;
}
export interface BResultsSoilsResource {
  SoilsCollection: BSoilWithCount[];
}
export interface BSoilWithCount {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
  plants_count: number;
}
export interface FCreateOrUpdateEvent {
  id?: number;
  plant_id: number;
  date: string;
  event_notes?: string;
  observation?: FObservation;
  soil?: FSoil;
  pot?: FPot;
  images: FBImageAssignedToEvent[];
}
export interface FObservation {
  id?: number;
  diseases?: string;
  stem_max_diameter?: number;
  height?: number;
  observation_notes?: string;
}
export interface FSoil {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
}
export interface FPot {
  id?: number;
  material: string;
  shape_top: FBShapeTop;
  shape_side: FBShapeSide;
  diameter_width: number;
}
export interface FEvent {
  id: number;
  plant_id: number;
  date: string;
  event_notes?: string;
  observation?: FObservation;
  soil?: FSoil;
  pot?: FPot;
  images?: FBImageAssignedToEvent[];
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
    [k: string]: FCreateOrUpdateEvent[];
  };
}
export interface FSoilCreate {
  id?: number;
  soil_name: string;
  mix?: string;
  description?: string;
}
