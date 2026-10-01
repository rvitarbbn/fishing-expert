/**
 * API types for the fishing expert application.
 */

export interface Location {
  name: string;
  latitude?: number | null;
  longitude?: number | null;
  structure?: string | null;
}

export interface Conditions {
  wave_height_m?: number | null;
  wave_direction?: string | null;
  wave_period_s?: number | null;
  wind_speed_kmh?: number | null;
  wind_direction?: string | null;
  water_clarity?: 'clear' | 'slightly_murky' | 'murky' | null;
  sea_state?: 'flat' | 'calm' | 'light_chop' | 'moderate' | 'working' | 'rough' | null;
  current_strength?: 'weak' | 'moderate' | 'strong' | null;
  desired_layer?: 'surface' | 'shallow' | 'midwater' | 'bottom' | null;
}

export interface Observations {
  foam?: boolean | null;
  baitfish_visible?: boolean | null;
  birds_diving?: boolean | null;
  surface_activity?: boolean | null;
  activity_distance?: 'near' | 'medium' | 'far' | null;
  estimated_depth_m?: number | null;
}

export interface Equipment {
  rod_cast_min_g: number;
  rod_cast_max_g: number;
  reel_size?: number | null;
  main_line_pe?: number | null;
  leader_mm?: number | null;
}

export interface RecommendationRequest {
  target_fish: string;
  fishing_time: string;
  location: Location;
  use_forecast?: boolean;
  conditions?: Conditions | null;
  observations?: Observations | null;
  equipment: Equipment;
}

export interface LureRecommendation {
  lure_type: string;
  lure_name_he: string;
  length_cm_range: [number, number];
  weight_g_range: [number, number];
  recommended_weight_g: number;
  color_family: string;
  working_layer: string;
  retrieve_method: string;
  retrieve_steps_he: string[];
  suitability_score: number;
  contributing_rule_ids: string[];
}

export interface AlternativeRecommendation {
  recommendation: LureRecommendation;
  switch_condition_he: string;
}

export interface DataQuality {
  completeness_score: number;
  forecast_confidence?: string | null;
  forecast_timestamp?: string | null;
  forecast_provider?: string | null;
  data_source: string;
}

export interface RecommendationResponse {
  recommendation_id: string;
  request_timestamp: string;
  primary: LureRecommendation;
  alternatives: AlternativeRecommendation[];
  normalized_conditions: Record<string, unknown>;
  reasons: string[];
  warnings: string[];
  missing_information: string[];
  equipment_compatibility: Record<string, unknown>;
  data_quality: DataQuality;
  rules_version: string;
  knowledge_version: string;
}

export interface FishSpecies {
  id: string;
  name_he: string;
  name_en: string;
  preferred_lures: string[];
  active_times: string[];
  habitats: string[];
  seasonality_note: string;
  legal_status: string;
  confidence: string;
}

export interface Lure {
  id: string;
  name_he: string;
  length_cm: [number, number];
  weight_g: [number, number];
  layers: string[];
  retrieves: string[];
  brand_neutral: boolean;
  notes_he?: string;
}
