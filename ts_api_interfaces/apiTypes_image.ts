import ManagedObject from "sap/ui/base/ManagedObject";

/**
 * @namespace plants.ui.definitions
 */
export type MessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface GenerateMissingThumbnails {
  count_already_existed: number;
  count_generated: number;
}
export interface PImage {
  filename: string;
  keywords: PKeyword[];
  plants: PImagePlantTag[];
  description?: string;
  record_date_time?: string;
}
export interface PKeyword {
  keyword: string;
}
export interface PImagePlantTag {
  plant_id?: number;
  key: string;
  text: string;
}
export interface PImageUpdated {
  ImagesCollection: PImage[];
}
export interface PImageUploadedMetadata {
  plants: number[];
  keywords: string[];
}
export interface PResultsImageDeleted {
  action: string;
  resource: string;
  message: PMessage;
}
export interface PResultsImageResource {
  ImagesCollection: PImage[];
  message: PMessage;
}
export interface PResultsImagesUploaded {
  action: string;
  resource: string;
  message: PMessage;
  images: PImage[];
}
