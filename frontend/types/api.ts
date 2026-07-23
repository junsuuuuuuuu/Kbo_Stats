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
  at_bats: number;
  runs: number;
  hits: number;
  doubles: number;
  triples: number;
  batting_average: number | null;
  on_base_percentage: number | null;
  slugging_percentage: number | null;
  on_base_plus_slugging: number | null;
  defensive_efficiency: number | null;
  team_rank: number | null;
  walk_percentage: number | null;
  strikeout_percentage: number | null;
  walk_to_strikeout_ratio: number | null;
  isolated_power: number | null;
  batting_average_on_balls_in_play: number | null;
  stolen_base_percentage: number | null;
  speed_score: number | null;
  weighted_stolen_base_runs: number | null;
  weighted_double_play_runs: number | null;
  weighted_on_base_average: number | null;
  weighted_runs_above_average: number | null;
  weighted_runs_created: number | null;
  weighted_runs_created_plus: number | null;
  home_runs: number;
  total_bases: number;
  runs_batted_in: number;
  stolen_bases: number;
  caught_stealing: number;
  walks: number;
  hit_by_pitch: number;
  strikeouts: number;
  grounded_into_double_play: number;
  sacrifice_flies: number;
  sacrifice_hits: number;
  errors: number;
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
  complete_games: number;
  shutouts: number;
  wins: number;
  losses: number;
  saves: number;
  holds: number;
  winning_percentage: number | null;
  batters_faced: number;
  innings_pitched: string;
  innings_pitched_outs: number;
  hits_allowed: number;
  home_runs_allowed: number;
  strikeouts: number;
  walks_allowed: number;
  hit_batters: number;
  runs_allowed: number;
  earned_runs: number;
  [key: string]: string | number | boolean | null;
}

export interface PlayerSeasons {
  player_id: number;
  batting: BattingSeason[];
  pitching: PitchingSeason[];
}

export interface PlayerOverview {
  player: PlayerDetail;
  seasons: PlayerSeasons;
}

export interface PitchingAppearance {
  game_date: string;
  opponent: string;
  appearance_type: string;
  result: string | null;
  game_era: number;
  batters_faced: number;
  innings_pitched: string;
  hits_allowed: number;
  home_runs_allowed: number;
  walks_allowed: number;
  hit_batters: number;
  strikeouts: number;
  runs_allowed: number;
  earned_runs: number;
  season_era: number;
}

export interface PitchingAppearances {
  player_id: number;
  season: number;
  source_url: string;
  items: PitchingAppearance[];
}

export interface BattingAppearance {
  game_date: string;
  opponent: string;
  game_average: number | null;
  plate_appearances: number;
  at_bats: number;
  runs: number;
  hits: number;
  doubles: number;
  triples: number;
  home_runs: number;
  runs_batted_in: number;
  stolen_bases: number;
  caught_stealing: number;
  walks: number;
  hit_by_pitch: number;
  strikeouts: number;
  grounded_into_double_play: number;
  season_average: number;
}

export interface BattingAppearances {
  player_id: number;
  season: number;
  source_url: string;
  items: BattingAppearance[];
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

export interface TeamStanding {
  season: number;
  as_of_date: string;
  team_code: string;
  team_name: string;
  ranking: number;
  games: number;
  wins: number;
  losses: number;
  draws: number;
  winning_percentage: number;
  games_behind: number;
  recent_ten: string;
  streak: string;
  home_record: string;
  away_record: string;
  source_url: string;
}

export interface TeamGameResult {
  game_date: string;
  opponent: string;
  venue: "home" | "away";
  result: "W" | "L" | "D";
  team_score: number;
  opponent_score: number;
  stadium: string;
  game_url: string | null;
  game_id: string | null;
}

export interface GameHitter {
  batting_order: string;
  position: string;
  player_name: string;
  at_bats: number;
  hits: number;
  runs_batted_in: number;
  runs: number;
  batting_average: number;
  plate_appearances: string[];
}

export interface GamePitcher {
  player_name: string;
  appearance: string;
  result: string | null;
  wins: number;
  losses: number;
  saves: number;
  innings_pitched: string;
  batters_faced: number;
  pitches: number;
  at_bats: number;
  hits_allowed: number;
  home_runs_allowed: number;
  walks_and_hit_batters: number;
  strikeouts: number;
  runs_allowed: number;
  earned_runs: number;
  earned_run_average: number;
}

export interface GameTeamBox {
  team_code: string;
  team_name: string;
  result: "W" | "L" | "D";
  runs: number;
  hits: number;
  errors: number;
  walks: number;
  innings: string[];
  hitters: GameHitter[];
  pitchers: GamePitcher[];
}

export interface TeamGameDetail {
  game_id: string;
  game_date: string;
  stadium: string;
  crowd: string;
  start_time: string;
  end_time: string;
  duration: string;
  away: GameTeamBox;
  home: GameTeamBox;
  key_events: [string, string][];
  source_url: string;
}

export interface TeamGameResults {
  season: number;
  team_code: string;
  source_url: string;
  items: TeamGameResult[];
}

export interface GameDayStar {
  player_name: string;
  summary: string;
}

export interface GameDayTeam {
  team_code: string;
  team_name: string;
  result: "W" | "L" | "D" | null;
  runs: number | null;
  hits: number | null;
  errors: number | null;
}

export interface LatestGameSummary {
  game_id: string;
  stadium: string;
  start_time: string;
  status: "completed" | "scheduled" | "cancelled";
  away: GameDayTeam;
  home: GameDayTeam;
  away_hitter: GameDayStar | null;
  away_pitcher: GameDayStar | null;
  home_hitter: GameDayStar | null;
  home_pitcher: GameDayStar | null;
  winning_pitcher: string | null;
  losing_pitcher: string | null;
  cancellation_reason: string | null;
  away_starting_pitcher: string | null;
  home_starting_pitcher: string | null;
}

export interface LatestGameDay {
  game_date: string;
  games: LatestGameSummary[];
  source_url: string;
}

export interface PlayerBenchmarks {
  player_id: number;
  role: AnalyticsRole;
  season: number;
  qualification: string;
  items: Array<{
    metric: string;
    player_value: number;
    league_average: number;
    percentile: number;
    sample_size: number;
    higher_is_better: boolean;
  }>;
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
  value_type: RankingValueType;
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

export type RankingValueType = "overall" | "offense" | "defense";

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
