export type PlayerRole = "BATTING" | "PITCHING";
export type AnalyticsRole = "batting" | "pitching";

export interface PlayerSummary {
  player_id: number;
  player_name: string;
  birth_date: string;
  roles: PlayerRole[];
}

export interface PlayerPage {
  items: PlayerSummary[];
  page: number;
  page_size: number;
  total: number;
}

export interface PlayerProfile {
  role: PlayerRole;
  source_url: string;
  bat_side: string;
  throw_side: string;
  height_cm: number | null;
  weight_kg: number | null;
  career: string | null;
  draft: string | null;
}

export interface PlayerDetail {
  player_id: number;
  player_name: string;
  birth_date: string;
  profiles: PlayerProfile[];
}

export interface BattingSeason {
  season: number;
  is_partial: boolean;
  as_of_date: string | null;
  age: number;
  team: string;
  position: string;
  games: number;
  plate_appearances: number;
  batting_average: number | null;
  on_base_percentage: number | null;
  slugging_percentage: number | null;
  on_base_plus_slugging: number | null;
  home_runs: number;
  runs_batted_in: number;
  stolen_bases: number;
  walks: number;
  strikeouts: number;
  [key: string]: string | number | boolean | null;
}

export interface PitchingSeason {
  season: number;
  is_partial: boolean;
  as_of_date: string | null;
  age: number;
  team: string;
  earned_run_average: number | null;
  games: number;
  wins: number;
  losses: number;
  saves: number;
  holds: number;
  innings_pitched: string;
  innings_pitched_outs: number;
  strikeouts: number;
  walks_allowed: number;
  [key: string]: string | number | boolean | null;
}

export interface PlayerSeasons {
  player_id: number;
  batting: BattingSeason[];
  pitching: PitchingSeason[];
}

export interface TeamSummary {
  team_id: number;
  team_code: string;
  team_name: string;
  season: number;
  as_of_date: string;
  roster_count: number;
  pitcher_count: number;
  hitter_count: number;
}

export interface TeamList {
  season: number;
  items: TeamSummary[];
}

export interface RosterMember {
  player_id: number;
  player_name: string;
  uniform_number: string;
  position: "P" | "C" | "IF" | "OF";
  position_label: string;
  bat_side: "L" | "R" | "S";
  throw_side: "L" | "R";
  birth_date: string;
  age: number;
  height_cm: number | null;
  weight_kg: number | null;
  source_url: string;
}

export interface TeamRoster {
  team: TeamSummary;
  members: RosterMember[];
}

export interface PredictionResponse {
  player_id: number;
  role: AnalyticsRole;
  base_season: number;
  predictions: Array<{
    target: string;
    target_season: number;
    prediction: number;
    previous_season_value: number;
  }>;
}

export interface GrowthPoint {
  season: number;
  age: number | null;
  team: string;
  metric: string;
  metric_label: string;
  value: number | null;
  absolute_change: number | null;
  growth_rate_pct: number | null;
  performance_change: number | null;
  change_percentile: number | null;
  event: "breakout" | "decline" | "stable" | "not_evaluated";
  evaluation_status: string;
}

export interface GrowthResponse {
  player: Record<string, unknown>;
  curves: GrowthPoint[];
  events: GrowthPoint[];
  summary: Array<Record<string, unknown>>;
}

export interface PeakResponse {
  player_id: number;
  player_name: string;
  role: AnalyticsRole;
  current_age: number | null;
  peak_timing: string;
  predictions: Record<string, number>;
  model_details: Record<string, {
    deployed_model: string;
    candidate_model: string;
    validation_mae: number | null;
    baseline_mae: number | null;
    uses_baseline_fallback: boolean;
  }>;
}

export interface SimilarResponse {
  reference: Record<string, unknown>;
  recommendations: Array<{
    rank: number;
    player_id: number;
    player_name: string;
    team: string;
    cosine_score: number;
    knn_score: number;
    similarity_score: number;
    reasons: string[];
  }>;
  pca_coordinates: Array<{
    player_id: number;
    player_name: string;
    pca_x: number;
    pca_y: number;
    is_reference: boolean;
  }>;
  pca_explained_variance_ratio: number[];
}

export interface RankingResponse {
  role: AnalyticsRole;
  season: number;
  items: Array<{
    season_rank: number;
    team_rank: number;
    player_id: number;
    player_name: string;
    team: string;
    age: number | null;
    ai_score: number;
    components: Record<string, number>;
    reasons: string[];
  }>;
}

export interface DiscoveryResponse {
  role: AnalyticsRole;
  season: number;
  items: Array<{
    player_id: number;
    player_name: string;
    season: number;
    team: string;
    age: number | null;
    stats: Record<string, number | null>;
  }>;
}
