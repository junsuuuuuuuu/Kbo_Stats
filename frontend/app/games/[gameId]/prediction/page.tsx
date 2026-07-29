"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BrainCircuit, Check, CircleAlert } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import { TeamLogo } from "@/components/team-logo";
import { ErrorPanel, LoadingPanel, MetricCard, SectionTitle } from "@/components/ui";
import { getGamePrediction } from "@/lib/game-prediction";
import { CURRENT_SEASON } from "@/lib/constants";
import type { GamePredictionResponse, GamePredictionTeam, RecentTeamMetrics } from "@/types/api";

type RecentMetricKey = keyof Pick<RecentTeamMetrics, "win_percentage" | "runs_for_per_game" | "runs_against_per_game" | "run_differential" | "batting_average" | "ops" | "era" | "whip" | "strikeouts_per_game">;

function TeamColumn({ team, side, favorite }: { team: GamePredictionTeam; side: "away" | "home"; favorite: boolean }) {
  return <div className={`prediction-team ${favorite ? "favorite" : ""}`}>
    <TeamLogo teamCode={team.code} teamName={team.name} />
    <span className="prediction-team-side">{side === "away" ? "원정" : "홈"}</span>
    <h2>{team.name}</h2>
    <strong>{team.win_probability}%</strong>
    <small>예상 {team.score ?? "데이터 없음"}점</small>
  </div>;
}

function ComparisonRow({ label, away, home }: { label: string; away: ReactNode; home: ReactNode }) {
  return <div className="prediction-comparison-row"><span>{away}</span><b>{label}</b><span>{home}</span></div>;
}

function RecentMetricValue({ team, metric, decimals }: { team: GamePredictionTeam; metric: RecentMetricKey; decimals: number }) {
  const value = team.recent[metric];
  if (value == null) return <span className="metric-empty">데이터 없음</span>;
  return <span className="recent-metric-value">{value.toFixed(decimals)}{team.recent.status === "partial" ? <small>부분 데이터</small> : null}</span>;
}

function recentScope(away: GamePredictionTeam, home: GamePredictionTeam) {
  const awayGames = away.recent.games;
  const homeGames = home.recent.games;
  if (awayGames != null && homeGames != null && awayGames === homeGames) return `최근 10경기 기준 · ${awayGames}경기 데이터`;
  if (awayGames != null || homeGames != null) return `최근 10경기 기준 · 원정 ${awayGames ?? "-"}경기 / 홈 ${homeGames ?? "-"}경기 데이터`;
  return "최근 10경기 기준";
}

function recentReasons(data: GamePredictionResponse) {
  const reasons: string[] = [];
  const comparisons: Array<[RecentMetricKey, string]> = [
    ["runs_for_per_game", "경기당 평균 득점"],
    ["run_differential", "경기당 득실차"],
    ["ops", "OPS"],
  ];
  for (const [key, label] of comparisons) {
    const away = data.away.recent[key];
    const home = data.home.recent[key];
    if (away == null || home == null || away === home) continue;
    const team = away > home ? data.away : data.home;
    const games = team.recent.games ?? 10;
    reasons.push(`${team.name}는 최근 ${games}경기에서 ${label}이 더 높습니다.`);
  }
  return reasons.length ? reasons : ["최근 10경기 데이터가 충분하지 않아 비교 가능한 지표만 반영했습니다."];
}

export default function GamePredictionPage() {
  const { gameId } = useParams<{ gameId: string }>();
  const prediction = useQuery({
    queryKey: ["game-prediction", gameId, CURRENT_SEASON],
    queryFn: () => getGamePrediction(gameId, CURRENT_SEASON),
    enabled: Boolean(gameId),
  });

  if (prediction.isLoading) return <div className="page"><LoadingPanel label="경기 예측 분석을 준비하고 있습니다" /></div>;
  if (prediction.isError || !prediction.data) return <div className="page"><ErrorPanel error={prediction.error} /></div>;

  const data = prediction.data;
  const favorite = data.favorite_team ? data[data.favorite_team] : null;
  const confidence = data.confidence === "high" ? "높음" : data.confidence === "low" ? "낮음" : data.confidence === "medium" ? "보통" : "산출 불가";

  return <div className="page game-prediction-page">
    <Link className="back-link" href="/"><ArrowLeft size={16} /> 경기 일정으로 돌아가기</Link>
    <SectionTitle eyebrow={`${data.season} Game Prediction`} title="경기 예측 분석" description="최근 경기 흐름과 팀 지표를 바탕으로 한 경기 전 예측입니다." />

    <section className="prediction-hero panel">
      <div className="prediction-meta"><span className="badge">{data.status === "scheduled" ? "예정 경기" : "예측 불가"}</span><strong>{data.game_date}</strong><span>{data.start_time} · {data.stadium}</span></div>
      {favorite ? <div className="prediction-verdict"><span className="eyebrow">예측 우세 팀</span><h2>{favorite.name}</h2><p>{favorite.win_probability}% 승리 확률 · 예상 스코어 {data.away.score ?? "-"} : {data.home.score ?? "-"}</p></div> : <div className="prediction-verdict unavailable"><CircleAlert /><h2>예측을 제공할 수 없습니다</h2><p>현재 경기 데이터가 충분하지 않습니다.</p></div>}
      <div className="prediction-teams"><TeamColumn team={data.away} side="away" favorite={data.favorite_team === "away"} /><div className="prediction-vs">VS</div><TeamColumn team={data.home} side="home" favorite={data.favorite_team === "home"} /></div>
    </section>

    <section className="metric-grid prediction-metric-grid">
      <MetricCard label="예측 신뢰도" value={confidence} hint="선발·표본에 따라 변동" />
      <MetricCard label="예상 스코어" value={`${data.away.score ?? "-"} : ${data.home.score ?? "-"}`} hint={`${data.away.name} : ${data.home.name}`} />
      <MetricCard label="원정 승리 확률" value={`${data.away.win_probability}%`} />
      <MetricCard label="홈 승리 확률" value={`${data.home.win_probability}%`} />
    </section>

    <section className="section two-column prediction-columns">
      <div className="panel"><div className="panel-header"><h2>주요 예측 근거</h2><Check size={19} /></div><ul className="prediction-reasons">{recentReasons(data).map((reason) => <li key={reason}>{reason}</li>)}</ul></div>
      <div className="panel"><div className="panel-header"><h2>AI 분석 설명</h2><BrainCircuit size={19} /></div><p className="prediction-analysis">{data.ai_analysis ?? "최근 10경기 분석 설명이 제공되지 않았습니다."}</p></div>
    </section>

    <section className="section panel"><div className="panel-header"><h2>팀 전력 비교</h2><span className="muted">최근·시즌·구장별 성적</span></div><div className="prediction-comparison"><ComparisonRow label="최근 10경기" away={data.away.comparison.recent_ten} home={data.home.comparison.recent_ten} /><ComparisonRow label="시즌 전적" away={data.away.comparison.season_record} home={data.home.comparison.season_record} /><ComparisonRow label="홈·원정 성적" away={data.away.comparison.home_away_record} home={data.home.comparison.home_away_record} /><ComparisonRow label="상대전적" away={data.away.comparison.head_to_head} home={data.home.comparison.head_to_head} /></div></section>

    <section className="section panel"><div className="panel-header"><h2>최근 10경기 타격·투수 지표</h2><span className="muted">{recentScope(data.away, data.home)}</span></div><div className="prediction-comparison">
      <ComparisonRow label="최근 10경기 평균 득점" away={<RecentMetricValue team={data.away} metric="runs_for_per_game" decimals={2} />} home={<RecentMetricValue team={data.home} metric="runs_for_per_game" decimals={2} />} />
      <ComparisonRow label="최근 10경기 평균 실점" away={<RecentMetricValue team={data.away} metric="runs_against_per_game" decimals={2} />} home={<RecentMetricValue team={data.home} metric="runs_against_per_game" decimals={2} />} />
      <ComparisonRow label="최근 10경기 득실차" away={<RecentMetricValue team={data.away} metric="run_differential" decimals={2} />} home={<RecentMetricValue team={data.home} metric="run_differential" decimals={2} />} />
      <ComparisonRow label="최근 10경기 타율" away={<RecentMetricValue team={data.away} metric="batting_average" decimals={3} />} home={<RecentMetricValue team={data.home} metric="batting_average" decimals={3} />} />
      <ComparisonRow label="최근 10경기 OPS" away={<RecentMetricValue team={data.away} metric="ops" decimals={3} />} home={<RecentMetricValue team={data.home} metric="ops" decimals={3} />} />
      <ComparisonRow label="최근 10경기 ERA" away={<RecentMetricValue team={data.away} metric="era" decimals={2} />} home={<RecentMetricValue team={data.home} metric="era" decimals={2} />} />
      <ComparisonRow label="최근 10경기 WHIP" away={<RecentMetricValue team={data.away} metric="whip" decimals={2} />} home={<RecentMetricValue team={data.home} metric="whip" decimals={2} />} />
      <ComparisonRow label="최근 10경기 경기당 탈삼진" away={<RecentMetricValue team={data.away} metric="strikeouts_per_game" decimals={2} />} home={<RecentMetricValue team={data.home} metric="strikeouts_per_game" decimals={2} />} />
    </div></section>

    <section className="section panel"><div className="panel-header"><h2>선발투수 분석</h2><span className="muted">경기 전 확정 정보</span></div><div className="prediction-starters"><Starter team={data.away} /><Starter team={data.home} /></div></section>
  </div>;
}

function Starter({ team }: { team: GamePredictionTeam }) {
  const pitcher = team.starting_pitcher;
  return <div className="prediction-starter"><span>{team.name}</span><strong>{pitcher?.name ?? "선발투수 미정"}</strong><small>{pitcher?.era != null ? `ERA ${pitcher.era.toFixed(2)}` : "선발 정보가 확정되면 분석에 반영됩니다."}{pitcher?.record ? ` · ${pitcher.record}` : ""}</small></div>;
}
