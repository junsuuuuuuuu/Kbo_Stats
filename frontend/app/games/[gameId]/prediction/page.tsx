"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BrainCircuit, Check, CircleAlert } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { TeamLogo } from "@/components/team-logo";
import { ErrorPanel, LoadingPanel, MetricCard, SectionTitle } from "@/components/ui";
import { getGamePrediction } from "@/lib/game-prediction";
import { CURRENT_SEASON } from "@/lib/constants";
import type { GamePredictionTeam } from "@/types/api";

function TeamColumn({ team, side, favorite }: { team: GamePredictionTeam; side: "away" | "home"; favorite: boolean }) {
  return <div className={`prediction-team ${favorite ? "favorite" : ""}`}>
    <TeamLogo teamCode={team.code} teamName={team.name} />
    <span className="prediction-team-side">{side === "away" ? "원정" : "홈"}</span>
    <h2>{team.name}</h2>
    <strong>{team.win_probability}%</strong>
    <small>예상 {team.score}점</small>
  </div>;
}

function ComparisonRow({ label, away, home }: { label: string; away: string | number | null; home: string | number | null }) {
  return <div className="prediction-comparison-row"><span>{away ?? "-"}</span><b>{label}</b><span>{home ?? "-"}</span></div>;
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
    <SectionTitle eyebrow={`${data.season} Game Prediction`} title="경기 예측 분석" description="경기 전 팀 지표와 최근 흐름을 바탕으로 한 승부 예측입니다." />

    <section className="prediction-hero panel">
      <div className="prediction-meta"><span className="badge">{data.status === "scheduled" ? "예정 경기" : "예측 불가"}</span><strong>{data.game_date}</strong><span>{data.start_time} · {data.stadium}</span></div>
      {favorite ? <div className="prediction-verdict"><span className="eyebrow">예측 우세 팀</span><h2>{favorite.name}</h2><p>{favorite.win_probability}% 승리 확률 · 예상 스코어 {data.away.score} : {data.home.score}</p></div> : <div className="prediction-verdict unavailable"><CircleAlert /><h2>예측을 제공할 수 없습니다</h2><p>현재 경기 데이터가 충분하지 않습니다.</p></div>}
      <div className="prediction-teams"><TeamColumn team={data.away} side="away" favorite={data.favorite_team === "away"} /><div className="prediction-vs">VS</div><TeamColumn team={data.home} side="home" favorite={data.favorite_team === "home"} /></div>
    </section>

    <section className="metric-grid prediction-metric-grid">
      <MetricCard label="예측 신뢰도" value={confidence} hint="선발·표본에 따라 변동" />
      <MetricCard label="예상 스코어" value={`${data.away.score} : ${data.home.score}`} hint={`${data.away.name} : ${data.home.name}`} />
      <MetricCard label="원정 승리 확률" value={`${data.away.win_probability}%`} />
      <MetricCard label="홈 승리 확률" value={`${data.home.win_probability}%`} />
    </section>

    <section className="section two-column prediction-columns">
      <div className="panel"><div className="panel-header"><h2>주요 예측 근거</h2><Check size={19} /></div><ul className="prediction-reasons">{data.key_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>
      <div className="panel"><div className="panel-header"><h2>AI 분석 설명</h2><BrainCircuit size={19} /></div><p className="prediction-analysis">{data.ai_analysis ?? "분석 설명이 제공되지 않았습니다."}</p></div>
    </section>

    <section className="section panel"><div className="panel-header"><h2>팀 전력 비교</h2><span className="muted">최근·시즌·구장별 성적</span></div><div className="prediction-comparison"><ComparisonRow label="최근 10경기" away={data.away.comparison.recent_ten} home={data.home.comparison.recent_ten} /><ComparisonRow label="시즌 전적" away={data.away.comparison.season_record} home={data.home.comparison.season_record} /><ComparisonRow label="홈·원정 성적" away={data.away.comparison.home_away_record} home={data.home.comparison.home_away_record} /><ComparisonRow label="상대전적" away={data.away.comparison.head_to_head} home={data.home.comparison.head_to_head} /></div></section>

    <section className="section panel"><div className="panel-header"><h2>타격·투수 지표</h2><span className="muted">시즌 누적 기준</span></div><div className="prediction-comparison"><ComparisonRow label="팀 타율" away={data.away.comparison.batting?.toFixed(3) ?? null} home={data.home.comparison.batting?.toFixed(3) ?? null} /><ComparisonRow label="팀 평균자책점" away={data.away.comparison.pitching?.toFixed(2) ?? null} home={data.home.comparison.pitching?.toFixed(2) ?? null} /></div></section>

    <section className="section panel"><div className="panel-header"><h2>선발투수 분석</h2><span className="muted">경기 전 확정 정보</span></div><div className="prediction-starters"><Starter team={data.away} /><Starter team={data.home} /></div></section>
  </div>;
}

function Starter({ team }: { team: GamePredictionTeam }) {
  const pitcher = team.starting_pitcher;
  return <div className="prediction-starter"><span>{team.name}</span><strong>{pitcher?.name ?? "선발투수 미정"}</strong><small>{pitcher?.era != null ? `ERA ${pitcher.era.toFixed(2)}` : "선발 정보가 확정되면 분석에 반영됩니다."}{pitcher?.record ? ` · ${pitcher.record}` : ""}</small></div>;
}
