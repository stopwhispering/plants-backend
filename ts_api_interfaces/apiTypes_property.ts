
export type BMessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface BPropertyCollectionTaxon {
  categories: {
    [k: string]: FBPropertiesInCategory;
  };
}
export interface FBPropertiesInCategory {
  category_name: string;
  category_id: number;
  sort?: number;
  properties: FBProperty[];
  property_value?: string;
}
export interface FBProperty {
  property_name: string;
  property_name_id?: number;
  property_values: FBPropertyValue[];
  property_value?: string;
  property_value_id?: number;
}
export interface FBPropertyValue {
  type: string;
  property_value: string;
  property_value_id?: number;
}
export interface BPropertyName {
  property_name_id?: number;
  property_name: string;
  countPlants: number;
}
export interface BResultsPropertiesForPlant {
  action: string;
  resource: string;
  message: BMessage;
  propertyCollections: FBPropertyCollectionPlant;
  plant_id: number;
  propertyCollectionsTaxon: BPropertyCollectionTaxon;
  taxon_id?: number;
}
export interface FBPropertyCollectionPlant {
  categories: FBPropertiesInCategory[];
}
export interface BResultsPropertyNames {
  action: string;
  resource: string;
  message: BMessage;
  propertiesAvailablePerCategory: {
    [k: string]: BPropertyName[];
  };
}
export interface FPropertiesModifiedPlant {
  modifiedPropertiesPlants: {
    [k: string]: FBPropertyCollectionPlant;
  };
}
export interface FPropertiesModifiedTaxon {
  modifiedPropertiesTaxa: {
    [k: string]: {
      [k: string]: FBPropertiesInCategory;
    };
  };
}
