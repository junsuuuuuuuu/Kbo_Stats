"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CircleAlert } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type ReactNode } from "react";

import { TeamLogo } from "@/components/team-logo";
import { ErrorPanel, LoadingPanel, MetricCard, SectionTitle } from "@/components/ui";
import { CURRENT_SEASON } from "@/lib/constants";
import { getGamePrediction } from "@/lib/game-prediction";
import type {
  GamePredictionResponse,
  GamePredictionTeam,
  OpponentPitchingMetrics,
  RecentTeamMetrics,
  SeasonPitchingMetrics,
} from "@/types/api";

type RecentMetricKey = keyof Pick<RecentTeamMetrics, "runs_for_per_game" | "runs_against_per_game" | "run_differential" | "batting_average" | "on_base_percentage" | "slugging_percentage" | "ops" | "era" | "whip" | "strikeouts_per_game" | "home_runs" | "walks" | "hits_per_game">;

function TeamColumn({ team, side, favorite }: { team: GamePredictionTeam; side: "away" | "home"; favorite: boolean }) {
  return <div className={`prediction-team ${favorite ? "favorite" : ""}`}><TeamLogo teamCode={team.code} teamName={team.name} /><span className="prediction-team-side">{side === "away" ? "원정" : "홈"}</span><h2>{team.name}</h2><strong>{team.win_probability}%</strong><small>예상 {team.score ?? "데이터 없음"}점</small></div>;
}

function ComparisonRow({ label, away, home }: { label: string; away: ReactNode; home: ReactNode }) {
  return <div className="prediction-comparison-row"><span>{away}</span><b>{label}</b><span>{home}</span></div>;
}

function RecentMetricValue({ team, metric, decimals }: { team: GamePredictionTeam; metric: RecentMetricKey; decimals: number }) {
  const value = team.recent[metric];
  if (value == null) return <span className="metric-empty">데이터 없음</span>;
  return <span className="recent-metric-value">{value.toFixed(decimals)}</span>;
}

function dataStatus(team: GamePredictionTeam, kind: "batting" | "pitching") {
  const status = kind === "batting" ? team.recent.batting_status : team.recent.pitching_status;
  if (status === "complete") return `박스스코어 ${team.recent.boxscore_games}/${team.recent.expected_boxscore_games}경기 확보`;
  if (status === "partial") return `박스스코어 ${team.recent.boxscore_games}/${team.recent.expected_boxscore_games}경기 확보 · 일부 데이터`;
  return "박스스코어 없음";
}

function TeamMetricsPanel({ data }: { data: GamePredictionResponse }) {
  const [tab, setTab] = useState<"batting" | "pitching">("batting");
  const isBatting = tab === "batting";
  const metrics = isBatting
    ? [
        ["최근 10경기 평균 득점", "runs_for_per_game", 2],
        ["최근 10경기 평균 안타", "hits_per_game", 2],
        ["최근 10경기 타율", "batting_average", 3],
        ["최근 10경기 출루율", "on_base_percentage", 3],
        ["최근 10경기 장타율", "slugging_percentage", 3],
        ["최근 10경기 OPS", "ops", 3],
        ["최근 10경기 홈런", "home_runs", 0],
        ["최근 10경기 볼넷", "walks", 0],
      ] as const
    : [
        ["최근 10경기 평균 실점", "runs_against_per_game", 2],
        ["최근 10경기 득실차", "run_differential", 2],
        ["최근 10경기 ERA", "era", 2],
        ["최근 10경기 WHIP", "whip", 2],
        ["최근 10경기 경기당 탈삼진", "strikeouts_per_game", 2],
      ] as const;

  return <section className="section panel team-metrics-panel"><div className="panel-header"><div><h2>팀 타격·투수 지표</h2><span className="muted">예측 대상 경기 이전 최근 10경기 기준</span></div><div className="prediction-tabs" role="tablist"><button type="button" className={isBatting ? "active" : ""} onClick={() => setTab("batting")} role="tab" aria-selected={isBatting}>타격 지표</button><button type="button" className={!isBatting ? "active" : ""} onClick={() => setTab("pitching")} role="tab" aria-selected={!isBatting}>투수 지표</button></div></div><div className="metric-data-status"><span>{data.away.name}: {dataStatus(data.away, tab)}</span><span>{data.home.name}: {dataStatus(data.home, tab)}</span></div><div className="prediction-comparison">{metrics.map(([label, metric, decimals]) => <ComparisonRow key={metric} label={label} away={<RecentMetricValue team={data.away} metric={metric} decimals={decimals} />} home={<RecentMetricValue team={data.home} metric={metric} decimals={decimals} />} />)}</div></section>;
}

function SeasonPitcherGroup({ metrics }: { metrics: SeasonPitchingMetrics | null }) {
  if (!metrics || metrics.status === "unavailable") return <div className="pitcher-group"><h3>시즌 전체 기록</h3><small>데이터 없음</small></div>;
  return <div className="pitcher-group"><h3>시즌 전체 기록</h3><div className="pitcher-stat-grid"><span>ERA <b>{metrics.era?.toFixed(2) ?? "-"}</b></span><span>WHIP <b>{metrics.whip?.toFixed(2) ?? "-"}</b></span><span>이닝 <b>{metrics.innings?.toFixed(1) ?? "-"}</b></span><span>탈삼진 <b>{metrics.strikeouts ?? "-"}</b></span><span>볼넷 <b>{metrics.walks ?? "-"}</b></span><span>피안타 <b>{metrics.hits ?? "-"}</b></span><span>승·패 <b>{metrics.wins ?? "-"}-{metrics.losses ?? "-"}</b></span><span>등판 <b>{metrics.games ?? "-"}</b></span></div></div>;
}

function OpponentPitcherGroup({ opponent, metrics }: { opponent: string; metrics: OpponentPitchingMetrics | null }) {
  if (!metrics || metrics.status === "unavailable" || metrics.games === 0) return <div className="pitcher-group"><h3>{opponent} 상대전적</h3><small>상대전적 없음</small></div>;
  return <div className="pitcher-group"><h3>{opponent} 상대전적</h3><small>{metrics.games}경기 · 선발 {metrics.starts}경기</small><div className="pitcher-stat-grid"><span>ERA <b>{metrics.era?.toFixed(2) ?? "-"}</b></span><span>WHIP <b>{metrics.whip?.toFixed(2) ?? "-"}</b></span><span>이닝 <b>{metrics.innings?.toFixed(1) ?? "-"}</b></span><span>탈삼진 <b>{metrics.strikeouts ?? "-"}</b></span><span>승·패 <b>{metrics.wins ?? "-"}-{metrics.losses ?? "-"}</b></span></div></div>;
}

function Starter({ team, opponent }: { team: GamePredictionTeam; opponent: string }) {
  const pitcher = team.starting_pitcher;
  const statusLabel = pitcher.status === "available" ? "예정 선발" : pitcher.status === "unavailable" ? "선발 미정" : "선수 매칭 확인 필요";
  return <div className="prediction-starter"><div className="prediction-starter-heading"><span>{team.name}</span><b className={`pitcher-status ${pitcher.status}`}>{statusLabel}</b></div><strong>{pitcher.name ?? "선발투수 미정"}</strong><div className="pitcher-analysis-groups"><SeasonPitcherGroup metrics={pitcher.season} /><OpponentPitcherGroup opponent={opponent} metrics={pitcher.vs_opponent} /></div></div>;
}

export default function GamePredictionPage() {
  const { gameId } = useParams<{ gameId: string }>();
  const prediction = useQuery({ queryKey: ["game-prediction", gameId, CURRENT_SEASON], queryFn: () => getGamePrediction(gameId, CURRENT_SEASON), enabled: Boolean(gameId) });
  if (prediction.isLoading) return <div className="page"><LoadingPanel label="경기 예측 분석을 준비하고 있습니다" /></div>;
  if (prediction.isError || !prediction.data) return <div className="page"><ErrorPanel error={prediction.error} /></div>;
  const data = prediction.data;
  const favorite = data.favorite_team ? data[data.favorite_team] : null;
  return <div className="page game-prediction-page"><Link className="back-link" href="/"><ArrowLeft size={16} /> 경기 일정으로 돌아가기</Link><SectionTitle eyebrow={`${data.season} Game Prediction`} title="경기 예측 분석" description="최근 경기 흐름과 시즌 선발투수 기록을 바탕으로 분석합니다." /><section className="prediction-hero panel"><div className="prediction-meta"><span className="badge">예정 경기</span><strong>{data.game_date}</strong><span>{data.start_time} · {data.stadium}</span></div>{favorite ? <div className="prediction-verdict"><span className="eyebrow">예측 우세 팀</span><h2>{favorite.name}</h2><p>{favorite.win_probability}% 승리 확률 · 예상 스코어 {data.away.score ?? "-"} : {data.home.score ?? "-"}</p></div> : <div className="prediction-verdict unavailable"><CircleAlert /><h2>예측을 제공할 수 없습니다</h2><p>비교 가능한 데이터가 부족합니다.</p></div>}<div className="prediction-teams"><TeamColumn team={data.away} side="away" favorite={data.favorite_team === "away"} /><div className="prediction-vs">VS</div><TeamColumn team={data.home} side="home" favorite={data.favorite_team === "home"} /></div></section><section className="metric-grid prediction-metric-grid"><MetricCard label="예측 신뢰도" value={data.confidence ?? "-"} /><MetricCard label="예상 스코어" value={`${data.away.score ?? "-"} : ${data.home.score ?? "-"}`} hint={`${data.away.name} : ${data.home.name}`} /><MetricCard label="원정 승리 확률" value={`${data.away.win_probability}%`} /><MetricCard label="홈 승리 확률" value={`${data.home.win_probability}%`} /></section><section className="section panel"><div className="panel-header"><h2>팀 전력 비교</h2><span className="muted">최근·시즌·홈·원정 기록</span></div><div className="prediction-comparison"><ComparisonRow label="최근 10경기" away={data.away.comparison.recent_ten} home={data.home.comparison.recent_ten} /><ComparisonRow label="시즌 전적" away={data.away.comparison.season_record} home={data.home.comparison.season_record} /><ComparisonRow label="홈·원정 성적" away={data.away.comparison.home_away_record} home={data.home.comparison.home_away_record} /><ComparisonRow label="상대전적" away={data.away.comparison.head_to_head} home={data.home.comparison.head_to_head} /></div></section><TeamMetricsPanel data={data} /><section className="section panel"><div className="panel-header"><h2>선발투수 분석</h2><span className="muted">시즌 전체 성적 · 상대 구단 전적</span></div><div className="prediction-starters"><Starter team={data.away} opponent={data.home.name} /><Starter team={data.home} opponent={data.away.name} /></div></section></div>;
}
