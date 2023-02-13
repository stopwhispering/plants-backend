
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface BImageUpdated {
  ImagesCollection: ImageCreateUpdate[];
}
export interface ImageCreateUpdate {
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
  plant_id: number;
  plant_name: string;
  plant_name_short: string;
}
export interface BResultsImageDeleted {
  action: string;
  message: BMessage;
}
export interface BResultsImageResource {
  action?: string;
  message: BMessage;
  ImagesCollection: ImageRead[];
}
export interface ImageRead {
  id: number;
  filename: string;
  keywords: FBKeyword[];
  plants: FBImagePlantTag[];
  description?: string;
  record_date_time?: string;
}
export interface BResultsImagesUploaded {
  action?: string;
  message: BMessage;
  images: ImageRead[];
}
export interface ImageBase {
  id: number;
  filename: string;
  keywords: FBKeyword[];
  plants: FBImagePlantTag[];
  description?: string;
  record_date_time?: string;
}
