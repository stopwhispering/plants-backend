import ManagedObject from "sap/ui/base/ManagedObject";

/**
 * @namespace plants.ui.definitions
 */
export type ShapeTop = "square" | "round" | "oval" | "hexagonal";
export type ShapeSide = "very flat" | "flat" | "high" | "very high";
export type PEvents = PEvent[];
export type MessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface PEvent {
  id: number;
  plant_id: number;
  date: string;
  event_notes?: string;
  observation?: PRObservation;
  soil?: PRSoil;
  pot?: PRPot;
  images?: PImage[];
}
export interface PRObservation {
  id?: number;
  diseases?: string;
  stem_max_diameter?: number;
  height?: number;
  observation_notes?: string;
}
export interface PRSoil {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
}
export interface PRPot {
  id?: number;
  material: string;
  shape_top: ShapeTop;
  shape_side: ShapeSide;
  diameter_width: number;
}
export interface PImage {
  id?: number;
  filename: string;
}
export interface PImageDelete {
  filename: string;
}
export interface PImagesDelete {
  images: PImageDelete[];
}
export interface PResultsEventResource {
  events: PEvents;
  message: PMessage;
}
export interface PResultsSoilsResource {
  SoilsCollection: PSoilWithCount[];
}
export interface PSoilWithCount {
  id: number;
  soil_name: string;
  mix?: string;
  description?: string;
  plants_count: number;
}
export interface PResultsUpdateCreateSoil {
  soil: PRSoil;
  message: PMessage;
}
export interface PSoilCreate {
  id?: number;
  soil_name: string;
  mix?: string;
  description?: string;
}
export interface RCreateOrUpdateEvent {
  id?: number;
  plant_id: number;
  date: string;
  event_notes?: string;
  observation?: PRObservation;
  soil?: PRSoil;
  pot?: PRPot;
  images: PImage[];
}
export interface RRequestCreateOrUpdateEvent {
  plants_to_events: {
    [k: string]: RCreateOrUpdateEvent[];
  };
}
