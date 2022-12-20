import ManagedObject from "sap/ui/base/ManagedObject";

/**
 * @namespace plants.ui.definitions
 */
export type MessageType = "Information" | "None" | "Success" | "Warning" | "Error" | "Debug";

export interface PPropertiesInCategory {
  category_name: string;
  category_id: number;
  sort?: number;
  properties: PProperty[];
  property_value?: string;
}
export interface PProperty {
  property_name: string;
  property_name_id?: number;
  property_values: PPropertyValue[];
  property_value?: string;
  property_value_id?: number;
}
export interface PPropertyValue {
  type: string;
  property_value: string;
  property_value_id?: number;
}
export interface PPropertiesModifiedPlant {
  modifiedPropertiesPlants: {
    [k: string]: PPropertyCollectionPlant;
  };
}
export interface PPropertyCollectionPlant {
  categories: PPropertiesInCategory[];
}
export interface PPropertiesModifiedTaxon {
  modifiedPropertiesTaxa: {
    [k: string]: {
      [k: string]: PPropertiesInCategory;
    };
  };
}
export interface PPropertyCollectionTaxon {
  categories: {
    [k: string]: PPropertiesInCategory;
  };
}
export interface PPropertyName {
  property_name_id?: number;
  property_name: string;
  countPlants: number;
}
export interface PResultsPropertiesForPlant {
  action: string;
  resource: string;
  message: PMessage;
  propertyCollections: PPropertyCollectionPlant;
  plant_id: number;
  propertyCollectionsTaxon: PPropertyCollectionTaxon;
  taxon_id?: number;
}
export interface PResultsPropertyNames {
  action: string;
  resource: string;
  message: PMessage;
  propertiesAvailablePerCategory: {
    [k: string]: PPropertyName[];
  };
}
