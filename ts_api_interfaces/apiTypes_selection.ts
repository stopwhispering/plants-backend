import ManagedObject from "sap/ui/base/ManagedObject";

/**
 * @namespace plants.ui.definitions
 */
export type MessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface PResultsSelection {
  action: string;
  resource: string;
  message: PMessage;
  Selection: PTaxonTreeRoot;
}
export interface PTaxonTreeRoot {
  TaxonTree: PTaxonTreeNode[];
}
export interface PTaxonTreeNode {
  key: string;
  level: number;
  count: number;
  nodes?: PTaxonTreeNode[];
  plant_ids?: number[];
}
