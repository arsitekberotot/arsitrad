export type ModuleId =
  | "regulation"
  | "permit"
  | "cooling"
  | "disaster"
  | "settlement";

export interface ModuleDescriptor {
  id: ModuleId;
  title: string;
  description: string;
}

export interface BootstrapData {
  app_title: string;
  disclaimer: string;
  default_question: string;
  quick_prompts: string[];
  modules: ModuleDescriptor[];
}

export interface HealthData {
  status: "ok";
  config_path: string;
  model_path: string;
  model_exists: boolean;
  sparse_index_exists: boolean;
  dense_enabled: boolean;
  app_title: string;
}

export interface ChatMessageInput {
  role: "user" | "assistant";
  content: string;
}

export interface Candidate {
  chunk_key: string;
  content: string;
  metadata: Record<string, unknown>;
  score: number;
  source: string;
}

export interface RetrievalPayload {
  question: string;
  standalone_query: string;
  expanded_queries: string[];
  filters: Record<string, unknown>;
  candidates: Candidate[];
  should_answer: boolean;
  confidence: number;
  message?: string | null;
}

export interface AskResponse {
  answer: string;
  used_model: boolean;
  model_path?: string | null;
  raw_text?: string | null;
  retrieval: RetrievalPayload;
}

export interface ModuleResponse {
  payload: Record<string, unknown>;
}

export interface PermitFormData {
  building_type: string;
  location: string;
  floor_area_m2: number;
  land_area_m2: number;
  building_height_m: number;
  building_function: string;
}

export interface CoolingFormData {
  dimensions: {
    length_m: number;
    width_m: number;
    height_m: number;
    floor_count: number;
  };
  orientation: string;
  materials: {
    wall_material: string;
    roof_material: string;
  };
  climate_zone: string;
  budget_idr?: number;
}

export interface DisasterFormData {
  location: string;
  disaster_type: string;
  building_type: string;
  damage_description: string;
  floor_area_m2?: number;
  photo_urls: string[];
}

export interface SettlementFormData {
  location: string;
  population_density: number;
  current_infrastructure: string;
  budget_constraint_idr: number;
  priority_goals: string[];
}
