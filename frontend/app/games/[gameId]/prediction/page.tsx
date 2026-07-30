"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BrainCircuit, Check, CircleAlert } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import { TeamLogo } from "@/components/team-logo";
import { ErrorPanel, LoadingPanel, MetricCard, SectionTitle } from "@/components/ui";
import { CURRENT_SEASON } from "@/lib/constants";
import { getGamePrediction } from "@/lib/game-prediction";
import type { GamePredictionResponse, GamePredictionTeam, RecentTeamMetrics, SeasonPitchingMetrics, OpponentPitchingMetrics } from "@/types/api";

type RecentMetricKey = keyof Pick<RecentTeamMetrics, "runs_for_per_game" | "runs_against_per_game" | "run_differential" | "batting_average" | "on_base_percentage" | "slugging_percentage" | "ops" | "era" | "whip" | "strikeouts_per_game" | "home_runs" | "walks">;

function TeamColumn({ team, side, favorite }: { team: GamePredictionTeam; side: "away" | "home"; favorite: boolean }) {
  return <div className={`prediction-team ${favorite ? "favorite" : ""}`}><TeamLogo teamCode={team.code} teamName={team.name} /><span className="prediction-team-side">{side === "away" ? "원정" : "홈"}</span><h2>{team.name}</h2><strong>{team.win_probability}%</strong><small>예상 {team.score ?? "데이터 없음"}점</small></div>;
}

function ComparisonRow({ label, away, home }: { label: string; away: ReactNode; home: ReactNode }) {
  return <div className="prediction-comparison-row"><span>{away}</span><b>{label}</b><span>{home}</span></div>;
}

function RecentMetricValue({ team, metric, decimals }: { team: GamePredictionTeam; metric: RecentMetricKey; decimals: number }) {
  const value = team.recent[metric];
  if (value == null) return <span className="metric-empty">데이터 없음</span>;
  const batting = ["batting_average", "on_base_percentage", "slugging_percentage", "ops", "home_runs", "walks"].includes(metric);
  const pitching = ["era", "whip", "strikeouts_per_game"].includes(metric);
  const status = batting ? team.recent.batting_status : pitching ? team.recent.pitching_status : team.recent.status;
  return <span className="recent-metric-value">{value.toFixed(decimals)}{status === "partial" ? <small>일부 데이터</small> : null}</span>;
}

function recentScope(away: GamePredictionTeam, home: GamePredictionTeam) {
  const a = away.recent.games;
  const h = home.recent.games;
  if (a != null && h != null && a === h) return `최근 10경기 · ${a}경기 집계`;
  if (a != null || h != null) return `최근 10경기 · 원정 ${a ?? "-"}경기 / 홈 ${h ?? "-"}경기 집계`;
  return "최근 10경기 기준";
}

function recentReasons(data: GamePredictionResponse) {
  const reasons: string[] = [];
  const checks: Array<[RecentMetricKey, string]> = [["ops", "최근 10경기 OPS"], ["runs_for_per_game", "최근 10경기 평균 득점"], ["run_differential", "최근 10경기 득실차"]];
  for (const [key, label] of checks) {
    const away = data.away.recent[key];
    const home = data.home.recent[key];
    if (away == null || home == null || away === home) continue;
    const team = away > home ? data.away : data.home;
    reasons.push(`${team.name}는 ${label}이 더 높습니다.`);
  }
  return reasons.length ? reasons : ["최근 10경기 데이터가 충분하지 않아 비교 가능한 지표만 반영했습니다."];
}

function reasonScope(reason: string) {
  if (reason.includes("최근")) return "최근 10경기";
  if (reason.includes("시즌")) return "시즌 전체";
  if (reason.includes("상대")) return "상대전적";
  if (reason.includes("홈") || reason.includes("원정")) return "홈·원정";
  return "모델 근거";
}

function displayPitcherStatus(status: string) {
  if (status === "available") return "예정 선발";
  if (status === "unavailable") return "선발 미정";
  return "매칭 불가";
}

function PitcherStat({ label, value, status, decimals = 2 }: { label: string; value: number | null | undefined; status: string; decimals?: number }) {
  return <span>{label} <b>{value == null || status === "unavailable" ? "데이터 없음" : value.toFixed(decimals)}</b></span>;
}

function PitcherRecord({ wins, losses, status }: { wins: number | null | undefined; losses: number | null | undefined; status: string }) {
  return <span>승·패 <b>{wins == null || losses == null || status === "unavailable" ? "데이터 없음" : `${wins}-${losses}`}</b></span>;
}

function SeasonPitcherGroup({ metrics }: { metrics: SeasonPitchingMetrics | null }) {
  const status = metrics?.status ?? "unavailable";
  return <div className="pitcher-group"><h3>시즌 전체 기준</h3>{!metrics || status === "unavailable" ? <small>데이터 없음</small> : <div className="pitcher-stat-grid"><PitcherStat label="ERA" value={metrics.era} status={status} /><PitcherStat label="WHIP" value={metrics.whip} status={status} /><PitcherStat label="이닝" value={metrics.innings} status={status} decimals={1} /><PitcherStat label="탈삼진" value={metrics.strikeouts} status={status} decimals={0} /><PitcherStat label="볼넷" value={metrics.walks} status={status} decimals={0} /><PitcherRecord wins={metrics.wins} losses={metrics.losses} status={status} /><PitcherStat label="등판" value={metrics.games} status={status} decimals={0} /></div>}{status === "partial" ? <small className="partial-note">일부 데이터</small> : null}</div>;
}

function OpponentPitcherGroup({ opponent, metrics }: { opponent: string; metrics: OpponentPitchingMetrics | null }) {
  const status = metrics?.status ?? "unavailable";
  return <div className="pitcher-group"><h3>{opponent} 상대전적</h3>{!metrics || status === "unavailable" || metrics.games === 0 ? <small>상대전적 데이터 없음</small> : <><small>상대전적 {metrics.games}경기 기준</small><div className="pitcher-stat-grid"><PitcherStat label="ERA" value={metrics.era} status={status} /><PitcherStat label="WHIP" value={metrics.whip} status={status} /><PitcherStat label="이닝" value={metrics.innings} status={status} decimals={1} /><PitcherStat label="탈삼진" value={metrics.strikeouts} status={status} decimals={0} /><PitcherRecord wins={metrics.wins} losses={metrics.losses} status={status} /></div></>}{status === "partial" ? <small className="partial-note">일부 데이터</small> : null}</div>;
}

function Starter({ team, opponent }: { team: GamePredictionTeam; opponent: string }) {
  const pitcher = team.starting_pitcher;
  return <div className="prediction-starter"><div className="prediction-starter-heading"><span>{team.name}</span><b className={`pitcher-status ${pitcher.status}`}>{displayPitcherStatus(pitcher.status)}</b></div><strong>{pitcher.name ?? "선발투수 미정"}</strong><div className="pitcher-analysis-groups"><SeasonPitcherGroup metrics={pitcher.season} /><OpponentPitcherGroup opponent={opponent} metrics={pitcher.vs_opponent} /></div></div>;
}

export default function GamePredictionPage() {
  const { gameId } = useParams<{ gameId: string }>();
  const prediction = useQuery({ queryKey: ["game-prediction", gameId, CURRENT_SEASON], queryFn: () => getGamePrediction(gameId, CURRENT_SEASON), enabled: Boolean(gameId) });
  if (prediction.isLoading) return <div className="page"><LoadingPanel label="경기 예측 분석을 준비하고 있습니다" /></div>;
  if (prediction.isError || !prediction.data) return <div className="page"><ErrorPanel error={prediction.error} /></div>;
  const data = prediction.data;
  const favorite = data.favorite_team ? data[data.favorite_team] : null;
  const confidence = data.confidence === "high" ? "높음" : data.confidence === "low" ? "낮음" : data.confidence === "medium" ? "보통" : "산출 불가";
  return <div className="page game-prediction-page"><Link className="back-link" href="/"><ArrowLeft size={16} /> 경기 일정으로 돌아가기</Link><SectionTitle eyebrow={`${data.season} Game Prediction`} title="경기 예측 분석" description="최근 경기 흐름과 팀 지표를 바탕으로 한 경기 전 예측입니다." />
    <section className="prediction-hero panel"><div className="prediction-meta"><span className="badge">{data.status === "scheduled" ? "예정 경기" : "예측 불가"}</span><strong>{data.game_date}</strong><span>{data.start_time} · {data.stadium}</span></div>{favorite ? <div className="prediction-verdict"><span className="eyebrow">예측 우세 팀</span><h2>{favorite.name}</h2><p>{favorite.win_probability}% 승리 확률 · 예상 스코어 {data.away.score ?? "-"} : {data.home.score ?? "-"}</p></div> : <div className="prediction-verdict unavailable"><CircleAlert /><h2>예측을 제공할 수 없습니다</h2><p>현재 경기 데이터가 충분하지 않습니다.</p></div>}<div className="prediction-teams"><TeamColumn team={data.away} side="away" favorite={data.favorite_team === "away"} /><div className="prediction-vs">VS</div><TeamColumn team={data.home} side="home" favorite={data.favorite_team === "home"} /></div></section>
    <section className="metric-grid prediction-metric-grid"><MetricCard label="예측 신뢰도" value={confidence} hint="선발·표본에 따라 변동" /><MetricCard label="예상 스코어" value={`${data.away.score ?? "-"} : ${data.home.score ?? "-"}`} hint={`${data.away.name} : ${data.home.name}`} /><MetricCard label="원정 승리 확률" value={`${data.away.win_probability}%`} /><MetricCard label="홈 승리 확률" value={`${data.home.win_probability}%`} /></section>
    <section className="section two-column prediction-columns"><div className="panel"><div className="panel-header"><h2>주요 예측 근거</h2><Check size={19} /></div><ul className="prediction-reasons">{(data.key_reasons.length ? data.key_reasons : recentReasons(data)).map((reason) => <li key={reason}><small>{reasonScope(reason)}</small>{reason}</li>)}</ul></div><div className="panel"><div className="panel-header"><h2>AI 분석 설명</h2><BrainCircuit size={19} /></div><p className="prediction-analysis">{data.ai_analysis ?? "최근 10경기 분석 설명이 제공되지 않았습니다."}</p></div></section>
    <section className="section panel"><div className="panel-header"><h2>팀 전력 비교</h2><span className="muted">최근·시즌·홈·원정 기준</span></div><div className="prediction-comparison"><ComparisonRow label="최근 10경기" away={data.away.comparison.recent_ten} home={data.home.comparison.recent_ten} /><ComparisonRow label="시즌 전적" away={data.away.comparison.season_record} home={data.home.comparison.season_record} /><ComparisonRow label="홈·원정 성적" away={data.away.comparison.home_away_record} home={data.home.comparison.home_away_record} /><ComparisonRow label="상대전적" away={data.away.comparison.head_to_head} home={data.home.comparison.head_to_head} /></div></section>
    <section className="section panel"><div className="panel-header"><h2>팀 타격·투수 지표</h2><span className="muted">{recentScope(data.away, data.home)}</span></div><div className="prediction-comparison"><ComparisonRow label="최근 10경기 평균 득점" away={<RecentMetricValue team={data.away} metric="runs_for_per_game" decimals={2} />} home={<RecentMetricValue team={data.home} metric="runs_for_per_game" decimals={2} />} /><ComparisonRow label="최근 10경기 평균 실점" away={<RecentMetricValue team={data.away} metric="runs_against_per_game" decimals={2} />} home={<RecentMetricValue team={data.home} metric="runs_against_per_game" decimals={2} />} /><ComparisonRow label="최근 10경기 득실차" away={<RecentMetricValue team={data.away} metric="run_differential" decimals={2} />} home={<RecentMetricValue team={data.home} metric="run_differential" decimals={2} />} /><ComparisonRow label="최근 10경기 타율" away={<RecentMetricValue team={data.away} metric="batting_average" decimals={3} />} home={<RecentMetricValue team={data.home} metric="batting_average" decimals={3} />} /><ComparisonRow label="최근 10경기 출루율" away={<RecentMetricValue team={data.away} metric="on_base_percentage" decimals={3} />} home={<RecentMetricValue team={data.home} metric="on_base_percentage" decimals={3} />} /><ComparisonRow label="최근 10경기 장타율" away={<RecentMetricValue team={data.away} metric="slugging_percentage" decimals={3} />} home={<RecentMetricValue team={data.home} metric="slugging_percentage" decimals={3} />} /><ComparisonRow label="최근 10경기 OPS" away={<RecentMetricValue team={data.away} metric="ops" decimals={3} />} home={<RecentMetricValue team={data.home} metric="ops" decimals={3} />} /><ComparisonRow label="최근 10경기 홈런" away={<RecentMetricValue team={data.away} metric="home_runs" decimals={0} />} home={<RecentMetricValue team={data.home} metric="home_runs" decimals={0} />} /><ComparisonRow label="최근 10경기 볼넷" away={<RecentMetricValue team={data.away} metric="walks" decimals={0} />} home={<RecentMetricValue team={data.home} metric="walks" decimals={0} />} /><ComparisonRow label="최근 10경기 ERA" away={<RecentMetricValue team={data.away} metric="era" decimals={2} />} home={<RecentMetricValue team={data.home} metric="era" decimals={2} />} /><ComparisonRow label="최근 10경기 WHIP" away={<RecentMetricValue team={data.away} metric="whip" decimals={2} />} home={<RecentMetricValue team={data.home} metric="whip" decimals={2} />} /><ComparisonRow label="최근 10경기 경기당 탈삼진" away={<RecentMetricValue team={data.away} metric="strikeouts_per_game" decimals={2} />} home={<RecentMetricValue team={data.home} metric="strikeouts_per_game" decimals={2} />} /></div></section>
    <section className="section panel"><div className="panel-header"><h2>선발투수 분석</h2><span className="muted">시즌 전체 성적 · 상대 구단 상대전적</span></div><div className="prediction-starters"><Starter team={data.away} opponent={data.home.name} /><Starter team={data.home} opponent={data.away.name} /></div></section>
  </div>;
}
