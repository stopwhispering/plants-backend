
export type FBShapeTop = "square" | "round" | "oval" | "hexagonal";
export type FBShapeSide = "very flat" | "flat" | "high" | "very high";
export type BEvents = FBEvent[];
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface FBEvent {
  id: number;
  plant_id: number;
  date: string;
  event_notes?: string;
  observation?: FBObservation;
  soil?: FBSoil;
  pot?: FBPot;
  images?: FBImageAssignedToEvent[];
}
export interface FBObservation {
  id?: number;
  diseases?: string;
  stem_max_diameter?: number;
  height?: number;
  observation_notes?: string;
}
export interface FBSoil {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
}
export interface FBPot {
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
  soil: FBSoil;
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
  observation?: FBObservation;
  soil?: FBSoil;
  pot?: FBPot;
  images: FBImage[];
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
