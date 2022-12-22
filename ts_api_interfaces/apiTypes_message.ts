import ManagedObject from "sap/ui/base/ManagedObject";

/**
 * @namespace plants.ui.definitions
 */
export type PMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface PConfirmation {
  action: string;
  resource: string;
  message: PMessage;
}
export interface PMessage {
  type: PMessageType;
  message: string;
  additionalText?: string;
  description?: string;
}
