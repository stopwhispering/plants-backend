
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface BResultsSelection {
  action: string;
  message: BMessage;
  Selection: BTaxonTreeRoot;
}
export interface BTaxonTreeRoot {
  TaxonTree: BTaxonTreeNode[];
}
export interface BTaxonTreeNode {
  key: string;
  level: number;
  count: number;
  nodes?: BTaxonTreeNode[];
  plant_ids?: number[];
}
