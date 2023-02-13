
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";
export type FBMajorResource = "PlantResource" | "ImageResource" | "TaxonResource" | "EventResource";

export interface BConfirmation {
  action: string;
  message: BMessage;
}
export interface BMessage {
  type: BMessageType;
  message: string;
  additionalText?: string;
  description?: string;
}
export interface BSaveConfirmation {
  resource: FBMajorResource;
  message: BMessage;
}
