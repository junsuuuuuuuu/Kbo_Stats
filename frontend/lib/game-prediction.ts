import { api, ApiError } from "@/lib/api";
import { CURRENT_SEASON } from "@/lib/constants";
import type { GamePredictionApiResponse, GamePredictionResponse, GamePredictionTeam } from "@/types/api";

const mockTeam = (name: string, code: string, probability: number, score: number): GamePredictionTeam => ({
  code,
  name,
  win_probability: probability,
  score,
  comparison: {
    recent_ten: name === "원정팀" ? "6승 4패" : "5승 5패",
    season_record: name === "원정팀" ? "42승 31패" : "39승 34패",
    home_away_record: name === "원정팀" ? "원정 20승 16패" : "홈 23승 14패",
    head_to_head: name === "원정팀" ? "상대전적 5승 3패" : "상대전적 3승 5패",
    batting: name === "원정팀" ? 0.276 : 0.268,
    pitching: name === "원정팀" ? 3.72 : 4.05,
  },
  starting_pitcher: { name: "선발 미정", era: null, record: null },
});

export function mockGamePrediction(gameId: string, season = CURRENT_SEASON): GamePredictionResponse {
  return {
    game_id: gameId,
    season,
    game_date: "2026-07-27",
    start_time: "18:30",
    stadium: "잠실야구장",
    status: "scheduled",
    confidence: "medium",
    favorite_team: "away",
    key_reasons: ["최근 10경기 승률 우세", "원정팀의 시즌 타격 지표가 높음", "상대전적에서 근소한 우위"],
    ai_analysis: "최근 경기 흐름과 시즌 누적 지표를 종합하면 원정팀이 근소하게 앞섭니다. 선발투수가 확정되면 예측 신뢰도가 달라질 수 있습니다.",
    away: mockTeam("원정팀", "AWAY", 58, 5),
    home: mockTeam("홈팀", "HOME", 42, 4),
  };
}

function recordLabel(record: { wins: number; losses: number; draws: number }) {
  return `${record.wins}승 ${record.losses}패${record.draws ? ` ${record.draws}무` : ""}`;
}

function normalizeTeam(team: GamePredictionApiResponse["away"], pitcher: GamePredictionApiResponse["away_starting_pitcher"]): GamePredictionTeam {
  return {
    code: team.team_code,
    name: team.team_name,
    win_probability: 0,
    score: 0,
    comparison: {
      recent_ten: team.metrics.status === "unavailable" ? "데이터 부족" : `${team.metrics.recent_runs_for_per_game ?? "-"} 득점 / ${team.metrics.recent_runs_against_per_game ?? "-"} 실점`,
      season_record: recordLabel(team.season_record),
      home_away_record: recordLabel(team.home_record.games ? team.home_record : team.away_record),
      head_to_head: "상대전적은 공통 기준 제공",
      batting: null,
      pitching: team.metrics.recent_run_differential,
    },
    starting_pitcher: { name: pitcher.name ?? "선발투수 미정", era: null, record: pitcher.note },
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
  return { ...data, status: data.favored_team_name ? "scheduled" : "unavailable", favorite_team: data.favored_team_code === data.away.team_code ? "away" : data.favored_team_code === data.home.team_code ? "home" : null, ai_analysis: data.explanation, away, home, confidence: data.confidence as GamePredictionResponse["confidence"] };
}

export async function getGamePrediction(gameId: string, season = CURRENT_SEASON) {
  try {
    return normalizePrediction(await api.gamePrediction(gameId, season));
  } catch (error) {
    // 백엔드 계약이 배포되기 전에도 페이지를 확인할 수 있도록 404만 mock으로 대체한다.
    if (error instanceof ApiError && error.status === 404) return mockGamePrediction(gameId, season);
    throw error;
  }
}
