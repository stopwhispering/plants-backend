import ManagedObject from "sap/ui/base/ManagedObject";

/**
 * @namespace plants.ui.definitions
 */
export type PImages = PImage[];
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
  ImagesCollection: PImages;
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
  ImagesCollection: PImages;
  message: PMessage;
}
export interface PResultsImagesUploaded {
  action: string;
  resource: string;
  message: PMessage;
  images: PImages;
}
