export type Budget = "low" | "medium" | "high";

export type RecommendationRequest = {
  location: string;
  budget?: Budget | null;
  cuisine: string;
  min_rating: number;
  optional_notes: string;
  include_unknown_cost: boolean;
  max_candidates?: number | null;
};

export type GroqMetadata = {
  model: string;
  base_url: string;
  used_fallback: boolean;
  detail?: string | null;
  prompt_version: string;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
};

export type RankedRestaurant = {
  rank: number;
  explanation: string;
  id: string;
  name: string;
  locality?: string;
  city_area?: string;
  cuisines?: string[];
  rating?: number | null;
  votes?: number | null;
  cost_for_two_inr?: number | null;
  [key: string]: unknown;
};

export type RecommendationResponse = {
  snapshot: string;
  source_count: number;
  candidate_count: number;
  ranked: RankedRestaurant[];
  summary?: string | null;
  groq?: GroqMetadata | null;
  empty_message?: string | null;
  llm_latency_ms?: number | null;
};

export type ApiErrorBody = {
  error?: string;
  message?: string;
  hint?: string;
  path?: string;
  detail?: unknown | Array<{ loc?: (string | number)[]; msg?: string; type?: string }>;
};
