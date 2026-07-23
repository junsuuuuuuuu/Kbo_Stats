import type {
  AnalyticsRole,
  BattingAppearances,
  DiscoveryResponse,
  GrowthResponse,
  PeakResponse,
  PlayerDetail,
  PlayerBenchmarks,
  PlayerPage,
  PlayerOverview,
  PitchingAppearances,
  PlayerSeasons,
  PredictionResponse,
  RankingResponse,
  RankingValueType,
  SimilarResponse,
  LatestGameDay,
  TeamList,
  TeamGameResults,
  TeamGameDetail,
  TeamRoster,
  TeamStanding,
} from "@/types/api";
import { CURRENT_SEASON, LAST_COMPLETE_SEASON } from "@/lib/constants";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
  signal?: AbortSignal,
) {
  const url = new URL(`${API_URL}${path}`);
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  });
  const response = await fetch(url, { headers: { Accept: "application/json" }, signal });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { error?: { message?: string } }
      | null;
    throw new ApiError(body?.error?.message ?? "데이터를 불러오지 못했습니다.", response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  searchPlayers: (query: string, role?: string, page = 1, signal?: AbortSignal) =>
    request<PlayerPage>("/players", { query: query || undefined, role, page, page_size: 30 }, signal),
  player: (id: number) => request<PlayerDetail>(`/players/${id}`),
  seasons: (id: number) => request<PlayerSeasons>(`/players/${id}/seasons`),
  playerOverview: (id: number) => request<PlayerOverview>(`/players/${id}/overview`),
  pitchingAppearances: (id: number, season = CURRENT_SEASON) =>
    request<PitchingAppearances>(`/players/${id}/pitching-appearances`, { season }),
  battingAppearances: (id: number, season = CURRENT_SEASON) =>
    request<BattingAppearances>(`/players/${id}/batting-appearances`, { season }),
  benchmarks: (id: number, role: AnalyticsRole, season: number) =>
    request<PlayerBenchmarks>(`/players/${id}/benchmarks`, { role: role.toUpperCase(), season }),
  teams: (season = CURRENT_SEASON) => request<TeamList>("/teams", { season }),
  teamRoster: (teamCode: string, season = CURRENT_SEASON) =>
    request<TeamRoster>(`/teams/${teamCode}/roster`, { season }),
  teamStanding: (teamCode: string, season = CURRENT_SEASON) =>
    request<TeamStanding | null>(`/teams/${teamCode}/standing`, { season }),
  teamGames: (teamCode: string, season = CURRENT_SEASON) =>
    request<TeamGameResults>(`/teams/${teamCode}/games`, { season }),
  teamGame: (teamCode: string, gameId: string, season = CURRENT_SEASON) =>
    request<TeamGameDetail>(`/teams/${teamCode}/games/${gameId}`, { season }),
  latestGames: (season = CURRENT_SEASON) =>
    request<LatestGameDay>("/teams/games/latest", { season }),
  gamesByDay: (gameDate: string, season = CURRENT_SEASON) =>
    request<LatestGameDay>("/teams/games/day", { game_date: gameDate, season }),
  prediction: (role: AnalyticsRole, id: number) =>
    request<PredictionResponse>(`/analytics/predictions/${role}/${id}`),
  growth: (role: AnalyticsRole, id: number, metrics: string) =>
    request<GrowthResponse>(`/analytics/growth/${role}/${id}`, { metrics }),
  peak: (role: AnalyticsRole, id: number) =>
    request<PeakResponse>(`/analytics/peak/${role}/${id}`),
  similar: (role: AnalyticsRole, id: number, season?: number) =>
    request<SimilarResponse>(`/analytics/similar/${role}/${id}`, { season, limit: 10 }),
  rankings: (role: AnalyticsRole, season = LAST_COMPLETE_SEASON, team?: string, limit = 30, valueType: RankingValueType = "overall") =>
    request<RankingResponse>("/analytics/rankings", { role, season, team, limit, value_type: valueType }),
  discover: (params: Record<string, string | number | boolean | undefined>) =>
    request<DiscoveryResponse>("/analytics/discover", params),
};
