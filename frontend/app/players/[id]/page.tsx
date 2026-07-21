"use client";

import { useQuery } from "@tanstack/react-query";
import type { Data } from "plotly.js";
import { BrainCircuit, ChartNoAxesCombined, Sparkles, Target } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { GrowthChart, LineChart, PcaChart } from "@/components/charts";
import { ErrorPanel, LoadingPanel, MetricCard } from "@/components/ui";
import { CareerRecordDashboard } from "@/features/players/career-record-dashboard";
import { BattingAppearanceTable } from "@/features/players/batting-appearance-table";
import { CareerTimeline } from "@/features/players/career-timeline";
import { DefenseDashboard } from "@/features/players/defense-dashboard";
import { OffenseDashboard } from "@/features/players/offense-dashboard";
import { PitchingAppearanceTable } from "@/features/players/pitching-appearance-table";
import { api } from "@/lib/api";
import { toChartNumber } from "@/lib/analytics";
import { formatMetric } from "@/lib/metrics";
import type { AnalyticsRole } from "@/types/api";

const labels: Record<string, string> = {
  batting_average: "AVG", on_base_percentage: "OBP", slugging_percentage: "SLG", on_base_plus_slugging: "OPS", defensive_efficiency: "팀 DER", home_runs: "HR", runs_batted_in: "RBI", stolen_bases: "SB", walks: "BB", strikeouts: "SO", earned_run_average: "ERA", innings_pitched_outs: "IP Outs", saves: "SV", holds: "HLD", peak_age: "Peak Age", peak_ops: "Peak OPS", peak_home_runs: "Peak HR", peak_era: "Peak ERA", peak_strikeouts: "Peak SO",
};

const countMetrics = new Set(["home_runs", "strikeouts", "walks_allowed"]);

export default function PlayerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const playerId = Number(id);
  const [selectedRole, setSelectedRole] = useState<AnalyticsRole | null>(null);
  const [activeView, setActiveView] = useState<"overview" | "offense" | "defense">("overview");
  const player = useQuery({ queryKey: ["player", playerId], queryFn: () => api.player(playerId), enabled: Number.isFinite(playerId) });
  const seasons = useQuery({ queryKey: ["seasons", playerId], queryFn: () => api.seasons(playerId), enabled: Number.isFinite(playerId) });

  const requestedRole = searchParams.get("role");
  const availableRequestedRole: AnalyticsRole | null = requestedRole === "pitching" && seasons.data?.pitching.length
    ? "pitching"
    : requestedRole === "batting" && seasons.data?.batting.length
      ? "batting"
      : null;
  const role: AnalyticsRole = selectedRole ?? availableRequestedRole ?? (seasons.data?.batting.length === 0 && seasons.data.pitching.length > 0 ? "pitching" : "batting");
  const rows = useMemo(() => role === "batting" ? seasons.data?.batting ?? [] : seasons.data?.pitching ?? [], [role, seasons.data]);
  const latest = rows.at(-1);
  const latestSeason = latest?.season;
  const latestCompleted = rows.findLast((row) => !row.is_partial);
  const analysisSeason = latestCompleted?.season;
  const growthMetrics = role === "batting" ? "batting_average,on_base_plus_slugging,home_runs" : "earned_run_average,strikeouts,walks_allowed";
  const prediction = useQuery({ queryKey: ["prediction", role, playerId], queryFn: () => api.prediction(role, playerId), enabled: analysisSeason === 2025 });
  const growth = useQuery({ queryKey: ["growth", role, playerId], queryFn: () => api.growth(role, playerId, growthMetrics), enabled: rows.length > 0 });
  const peak = useQuery({ queryKey: ["peak", role, playerId], queryFn: () => api.peak(role, playerId), enabled: rows.length >= 3 });
  const similar = useQuery({ queryKey: ["similar", role, playerId, analysisSeason], queryFn: () => api.similar(role, playerId, analysisSeason), enabled: Boolean(analysisSeason) });
  const benchmarks = useQuery({ queryKey: ["benchmarks", role, playerId, latestSeason], queryFn: () => api.benchmarks(playerId, role, latestSeason!), enabled: Boolean(latestSeason) });
  const appearances = useQuery({
    queryKey: ["pitching-appearances", playerId, 2026],
    queryFn: () => api.pitchingAppearances(playerId, 2026),
    enabled: role === "pitching" && seasons.data?.pitching.some((row) => row.season === 2026),
  });
  const battingAppearances = useQuery({
    queryKey: ["batting-appearances", playerId, 2026],
    queryFn: () => api.battingAppearances(playerId, 2026),
    enabled: role === "batting" && seasons.data?.batting.some((row) => row.season === 2026),
  });

  if (player.isLoading || seasons.isLoading) return <div className="page"><LoadingPanel /></div>;
  if (player.isError || seasons.isError) return <div className="page"><ErrorPanel error={player.error ?? seasons.error} /></div>;

  const chartMetrics = role === "batting" ? ["batting_average", "on_base_plus_slugging", "home_runs"] : ["earned_run_average", "strikeouts", "walks_allowed"];
  const traces: Data[] = chartMetrics.map((metric) => ({
    type: "scatter",
    mode: "lines+markers",
    name: labels[metric],
    x: rows.map((row) => row.season),
    y: rows.map((row) => toChartNumber(row[metric])),
    yaxis: countMetrics.has(metric) ? "y2" : "y",
    connectgaps: false,
    line: { width: 3 },
  }));
  const latestMetrics = role === "batting" ? ["batting_average", "on_base_plus_slugging", "home_runs", "runs_batted_in"] : ["earned_run_average", "innings_pitched_outs", "strikeouts", "walks_allowed"];

  return (
    <div className="page player-detail-page">
      <header className="player-heading">
        <div>
          <span className="eyebrow">PLAYER INTELLIGENCE · {latestSeason ?? "—"}{latest?.is_partial ? " 진행 중" : ""}</span>
          <h1>{player.data?.player_name}</h1>
          <p className="muted">{player.data?.birth_date} · {latest?.team ?? "팀 정보 없음"}</p>
        </div>
        <div className="tabs">
          {seasons.data?.batting.length ? <button className={role === "batting" ? "active" : ""} onClick={() => { setSelectedRole("batting"); }}>타자</button> : null}
          {seasons.data?.pitching.length ? <button className={role === "pitching" ? "active" : ""} onClick={() => { setSelectedRole("pitching"); setActiveView("overview"); }}>투수</button> : null}
        </div>
      </header>

      <nav className="player-view-tabs" aria-label="선수 상세 항목">
        <button className={activeView === "overview" ? "active" : ""} onClick={() => setActiveView("overview")} type="button">종합 기록</button>
        {role === "batting" ? <button className={activeView === "offense" ? "active" : ""} onClick={() => setActiveView("offense")} type="button">공격 지표</button> : null}
        {role === "batting" ? <button className={activeView === "defense" ? "active" : ""} onClick={() => setActiveView("defense")} type="button">수비 지표</button> : null}
      </nav>

      {activeView === "offense" && role === "batting" ? (
        <OffenseDashboard rows={seasons.data?.batting ?? []} />
      ) : activeView === "defense" && role === "batting" ? (
        <DefenseDashboard rows={seasons.data?.batting ?? []} />
      ) : (

      <div className="player-detail-layout">
      <main className="player-detail-main">
      <section className={`metric-grid player-metric-grid ${role}`}>
        {latestMetrics.map((metric) => {
          const value = latest?.[metric];
          const snapshotHint = latest?.is_partial && latest.as_of_date ? ` · ${latest.as_of_date} 기준` : "";
          return <MetricCard key={metric} label={labels[metric]} value={formatMetric(metric, value == null ? null : Number(value))} hint={`${latestSeason ?? ""} 시즌${snapshotHint}`} />;
        })}
      </section>

      <section className="section benchmark-section">
        <div className="panel-header benchmark-heading">
          <div><span className="eyebrow">LEAGUE CONTEXT · {latestSeason}</span><h2>리그에서 어느 정도일까요?</h2></div>
          <p className="muted">{benchmarks.data?.qualification ?? "동일 시즌"} 선수 기준</p>
        </div>
        {benchmarks.isLoading ? <LoadingPanel label="리그 분포를 계산하고 있습니다" /> : benchmarks.isError ? <ErrorPanel error={benchmarks.error} /> : (
          <div className="benchmark-grid">
            {benchmarks.data?.items.map((item) => (
              <article className="benchmark-card" key={item.metric}>
                <div><span>{labels[item.metric] ?? item.metric}</span><strong>상위 {Math.max(1, Math.round(100 - item.percentile))}%</strong></div>
                <div className="percentile-track"><i style={{ width: `${item.percentile}%` }} /></div>
                <p>선수 <b>{formatMetric(item.metric, item.player_value)}</b><span>리그 평균 {formatMetric(item.metric, item.league_average)}</span></p>
              </article>
            ))}
          </div>
        )}
      </section>

      {role === "pitching" && latestSeason === 2026 ? (
        <PitchingAppearanceTable
          data={appearances.data}
          error={appearances.error}
          isError={appearances.isError}
          isLoading={appearances.isLoading}
        />
      ) : null}
      {role === "batting" && latestSeason === 2026 ? (
        <BattingAppearanceTable
          data={battingAppearances.data}
          error={battingAppearances.error}
          isError={battingAppearances.isError}
          isLoading={battingAppearances.isLoading}
        />
      ) : null}

      <CareerTimeline role={role} rows={rows} />

      <section className="section two-column">
        <div className="panel">
          <div className="panel-header"><h2>커리어 기록</h2><ChartNoAxesCombined size={20} /></div>
          <LineChart traces={traces} />
        </div>
        <div className="panel">
          <div className="panel-header"><h2>다음 시즌 AI 예측</h2><BrainCircuit size={20} /></div>
          {analysisSeason !== 2025 ? <div className="state-panel"><p>2025 완결 시즌 기록이 있는 현역 선수에게 제공됩니다.</p></div> : prediction.isLoading ? <LoadingPanel /> : prediction.isError ? <ErrorPanel error={prediction.error} /> : (
            <div className="metric-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
              {prediction.data?.predictions.map((item) => <MetricCard key={item.target} label={labels[item.target] ?? item.target} value={formatMetric(item.target, item.prediction)} hint={`이전 ${formatMetric(item.target, item.previous_season_value)}`} />)}
            </div>
          )}
        </div>
      </section>

      <CareerRecordDashboard key={role} role={role} rows={rows} />

      <section className="section panel">
        <div className="panel-header"><div><span className="eyebrow">CAREER TRAJECTORY</span><h2>성장곡선과 변곡점</h2></div><ChartNoAxesCombined size={20} /></div>
        {growth.isLoading ? <LoadingPanel /> : growth.isError ? <ErrorPanel error={growth.error} /> : growth.data && <GrowthChart points={growth.data.curves} />}
      </section>

      <section className="section panel">
          <div className="panel-header"><h2>전성기 예측</h2><Target size={20} /></div>
          {peak.isLoading ? <LoadingPanel /> : peak.isError ? <ErrorPanel error={peak.error} /> : (
            <div className="metric-grid" style={{ gridTemplateColumns: "repeat(3,1fr)" }}>
              {Object.entries(peak.data?.predictions ?? {}).map(([key, value]) => {
                const detail = peak.data?.model_details[key];
                const hint = detail?.uses_baseline_fallback
                  ? `기준 모델 적용 · ML ${detail.validation_mae?.toFixed(3)} / 기준 ${detail.baseline_mae?.toFixed(3)}`
                  : `${detail?.deployed_model ?? "ML"} · MAE ${detail?.validation_mae?.toFixed(3) ?? "—"}`;
                return <MetricCard key={key} label={labels[key] ?? key} value={formatMetric(key, value)} hint={hint} />;
              })}
            </div>
          )}
      </section>

      {similar.data && <section className="section panel"><div className="panel-header"><h2>플레이 스타일 PCA 맵</h2><span className="muted">기준 선수와 추천 TOP10</span></div><PcaChart data={similar.data} /></section>}
      </main>

      <aside className="panel similar-player-rail" aria-label="유사 선수 TOP10">
        <div className="panel-header"><div><span className="eyebrow">SIMILAR PLAYERS</span><h2>유사 선수 TOP10</h2></div><Sparkles size={19} /></div>
        {similar.isLoading ? <LoadingPanel /> : similar.isError ? <ErrorPanel error={similar.error} /> : (
          <ol className="similar-player-list">
            {similar.data?.recommendations.map((item) => (
              <li key={item.player_id}>
                <span className="rank">{item.rank}</span>
                <Link href={`/players/${item.player_id}?role=${role}`}>
                  <strong>{item.player_name}</strong>
                  <small>{item.team} · {item.reasons[0]}</small>
                </Link>
                <b>{(item.similarity_score * 100).toFixed(0)}</b>
              </li>
            ))}
          </ol>
        )}
      </aside>
      </div>
      )}
    </div>
  );
}
