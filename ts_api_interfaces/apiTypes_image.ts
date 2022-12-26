
export type FBImages = FBImage[];
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface BImageUpdated {
  ImagesCollection: FBImages;
}
export interface FBImage {
  id: number;
  filename: string;
  keywords: FBKeyword[];
  plants: FBImagePlantTag[];
  description?: string;
  record_date_time?: string;
}
export interface FBKeyword {
  keyword: string;
}
export interface FBImagePlantTag {
  plant_id?: number;
  key: string;
  text: string;
}
export interface BResultsImageDeleted {
  action: string;
  resource: string;
  message: BMessage;
}
export interface BResultsImageResource {
  ImagesCollection: FBImages;
  message: BMessage;
}
export interface BResultsImagesUploaded {
  action: string;
  message: BMessage;
  images: FBImages;
}
export interface FImageUploadedMetadata {
  plants: number[];
  keywords: string[];
}
