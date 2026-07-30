import { api } from "@/lib/api";
import { CURRENT_SEASON } from "@/lib/constants";
import type {
  GamePredictionApiResponse,
  GamePredictionResponse,
  GamePredictionTeam,
  RecentTeamMetrics,
  StartingPitcherAnalysis,
} from "@/types/api";

function recordLabel(record: { wins: number; losses: number; draws: number }) {
  return `${record.wins}승 ${record.losses}패${record.draws ? ` ${record.draws}무` : ""}`;
}

function firstNumber(...values: Array<number | null | undefined>) {
  return values.find((value): value is number => value != null) ?? null;
}

function normalizeRecentMetrics(metrics: GamePredictionApiResponse["away"]["metrics"]): RecentTeamMetrics {
  const status = metrics.recent_games_status ?? metrics.recent_status ?? metrics.status;
  return {
    games: metrics.recent_games_count ?? metrics.recent_games ?? null,
    boxscore_games: metrics.boxscore_games ?? 0,
    expected_boxscore_games: metrics.expected_boxscore_games ?? 0,
    status: status === "complete" ? "complete" : status === "partial" ? "partial" : "unavailable",
    win_percentage: metrics.recent_win_percentage ?? null,
    runs_for_per_game: metrics.recent_runs_for_per_game,
    runs_against_per_game: metrics.recent_runs_against_per_game,
    run_differential: metrics.recent_run_differential,
    batting_average: firstNumber(metrics.recent_batting_average, metrics.recent_avg),
    on_base_percentage: metrics.recent_on_base_percentage ?? null,
    slugging_percentage: metrics.recent_slugging_percentage ?? null,
    ops: firstNumber(metrics.recent_ops, metrics.recent_on_base_plus_slugging),
    hits_per_game: metrics.recent_hits_per_game ?? null,
    home_runs: metrics.recent_home_runs ?? null,
    walks: metrics.recent_walks ?? null,
    era: firstNumber(metrics.recent_era, metrics.recent_earned_run_average),
    whip: firstNumber(metrics.recent_whip, metrics.recent_walks_hits_per_inning),
    strikeouts_per_game: metrics.recent_strikeouts_per_game ?? null,
    batting_status: normalizeStatus(metrics.batting_status ?? status),
    pitching_status: normalizeStatus(metrics.pitching_status ?? status),
    batting_average_status: metrics.recent_batting_average_status ?? metrics.batting_status ?? status,
    on_base_percentage_status: metrics.recent_on_base_percentage_status ?? metrics.batting_status ?? status,
    slugging_percentage_status: metrics.recent_slugging_percentage_status ?? metrics.batting_status ?? status,
    ops_status: metrics.recent_ops_status ?? metrics.batting_status ?? status,
  };
}

function normalizeStatus(value: string | null | undefined): RecentTeamMetrics["status"] {
  return value === "complete" || value === "available" ? "complete" : value === "partial" ? "partial" : "unavailable";
}

function normalizeTeam(
  team: GamePredictionApiResponse["away"],
  pitcher: StartingPitcherAnalysis,
): GamePredictionTeam {
  const recent = normalizeRecentMetrics(team.metrics);
  return {
    code: team.team_code,
    name: team.team_name,
    win_probability: 0,
    score: 0,
    recent,
    comparison: {
      recent_ten: recent.games == null ? "최근 10경기 데이터 없음" : `${recent.games}경기 데이터`,
      season_record: recordLabel(team.season_record),
      home_away_record: recordLabel(team.home_record.games ? team.home_record : team.away_record),
      head_to_head: "상대전적 데이터 없음",
      batting: recent.batting_average,
      pitching: recent.era,
    },
    starting_pitcher: {
      ...pitcher,
      name: pitcher.name ?? "선발투수 미정",
    },
  };
}

function normalizePrediction(data: GamePredictionApiResponse): GamePredictionResponse {
  const away = normalizeTeam(data.away, data.away_starting_pitcher);
  const home = normalizeTeam(data.home, data.home_starting_pitcher);
  away.win_probability = Math.round(data.away_win_probability * 100);
  home.win_probability = Math.round(data.home_win_probability * 100);
  away.score = data.expected_score.away;
  home.score = data.expected_score.home;
  away.comparison.head_to_head = recordLabel(data.head_to_head);
  home.comparison.head_to_head = recordLabel(data.head_to_head);

  return {
    ...data,
    status: data.favored_team_name ? "scheduled" : "unavailable",
    favorite_team: data.favored_team_code === data.away.team_code
      ? "away"
      : data.favored_team_code === data.home.team_code
        ? "home"
        : null,
    ai_analysis: data.explanation,
    away,
    home,
    confidence: data.confidence as GamePredictionResponse["confidence"],
  };
}

export async function getGamePrediction(gameId: string, season = CURRENT_SEASON) {
  return normalizePrediction(await api.gamePrediction(gameId, season));
}
