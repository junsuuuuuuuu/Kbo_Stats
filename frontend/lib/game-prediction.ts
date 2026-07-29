import { api } from "@/lib/api";
import { CURRENT_SEASON } from "@/lib/constants";
import type {
  GamePredictionApiResponse,
  GamePredictionResponse,
  GamePredictionTeam,
} from "@/types/api";

function recordLabel(record: { wins: number; losses: number; draws: number }) {
  const draws = record.draws ? ` ${record.draws}무` : "";
  return `${record.wins}승 ${record.losses}패${draws}`;
}

function normalizeTeam(
  team: GamePredictionApiResponse["away"],
  pitcher: GamePredictionApiResponse["away_starting_pitcher"],
): GamePredictionTeam {
  return {
    code: team.team_code,
    name: team.team_name,
    win_probability: 0,
    score: 0,
    comparison: {
      recent_ten: team.metrics.status === "unavailable"
        ? "데이터 부족"
        : `${team.metrics.recent_runs_for_per_game ?? "-"} 득점 / ${team.metrics.recent_runs_against_per_game ?? "-"} 실점`,
      season_record: recordLabel(team.season_record),
      home_away_record: recordLabel(team.home_record.games ? team.home_record : team.away_record),
      head_to_head: "상대전적 공통 기준 제공",
      batting: null,
      pitching: team.metrics.recent_run_differential,
    },
    starting_pitcher: {
      name: pitcher.name ?? "선발투수 미정",
      era: null,
      record: pitcher.note,
    },
  };
}

function normalizePrediction(data: GamePredictionApiResponse): GamePredictionResponse {
  const away = normalizeTeam(data.away, data.away_starting_pitcher);
  const home = normalizeTeam(data.home, data.home_starting_pitcher);
  away.win_probability = Math.round(data.away_win_probability * 100);
  home.win_probability = Math.round(data.home_win_probability * 100);
  away.score = data.expected_score.away ?? 0;
  home.score = data.expected_score.home ?? 0;
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
