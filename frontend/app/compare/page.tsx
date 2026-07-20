"use client";

import { useQuery } from "@tanstack/react-query";
import type { Data } from "plotly.js";
import { useMemo, useState } from "react";

import { LineChart, RadarChart } from "@/components/charts";
import { PlayerPicker } from "@/components/player-picker";
import { ErrorPanel, LoadingPanel, SectionTitle } from "@/components/ui";
import { api } from "@/lib/api";
import { latestCommonSeason, toChartNumber } from "@/lib/analytics";
import type { AnalyticsRole, PlayerSummary } from "@/types/api";

const battingMetrics = ["batting_average", "on_base_percentage", "slugging_percentage", "on_base_plus_slugging", "home_runs", "runs_batted_in"];
const pitchingMetrics = ["earned_run_average", "innings_pitched_outs", "strikeouts", "walks_allowed", "saves", "holds"];
const metricLabels: Record<string, string> = { batting_average: "AVG", on_base_percentage: "OBP", slugging_percentage: "SLG", on_base_plus_slugging: "OPS", home_runs: "HR", runs_batted_in: "RBI", earned_run_average: "ERA 역점수", innings_pitched_outs: "IP", strikeouts: "SO", walks_allowed: "BB 역점수", saves: "SV", holds: "HLD" };

export default function ComparePage() {
  const [first, setFirst] = useState<PlayerSummary | null>(null);
  const [second, setSecond] = useState<PlayerSummary | null>(null);
  const [role, setRole] = useState<AnalyticsRole>("batting");
  const firstQuery = useQuery({ queryKey: ["compare-season", first?.player_id], queryFn: () => api.seasons(first!.player_id), enabled: Boolean(first) });
  const secondQuery = useQuery({ queryKey: ["compare-season", second?.player_id], queryFn: () => api.seasons(second!.player_id), enabled: Boolean(second) });

  const comparison = useMemo(() => {
    if (!first || !second || !firstQuery.data || !secondQuery.data) return null;
    const aRows = role === "batting" ? firstQuery.data.batting : firstQuery.data.pitching;
    const bRows = role === "batting" ? secondQuery.data.batting : secondQuery.data.pitching;
    const comparisonSeason = latestCommonSeason(aRows.map((row) => row.season), bRows.map((row) => row.season));
    const a = aRows.find((row) => row.season === comparisonSeason);
    const b = bRows.find((row) => row.season === comparisonSeason);
    if (!a || !b) return null;

    const candidates = role === "batting" ? battingMetrics : pitchingMetrics;
    const metrics = candidates.filter((metric) => a[metric] != null && b[metric] != null);
    const normalized = metrics.map((metric) => {
      let av = Number(a[metric]);
      let bv = Number(b[metric]);
      if (["earned_run_average", "walks_allowed"].includes(metric)) {
        const ceiling = Math.max(av, bv, 1);
        av = ceiling - av;
        bv = ceiling - bv;
      }
      const max = Math.max(av, bv, 0.0001);
      return [av / max * 100, bv / max * 100];
    });
    return { aRows, bRows, metrics, comparisonSeason, aValues: normalized.map((value) => value[0]), bValues: normalized.map((value) => value[1]) };
  }, [first, second, firstQuery.data, secondQuery.data, role]);

  const careerMetric = role === "batting" ? "on_base_plus_slugging" : "earned_run_average";
  const lineTraces: Data[] = comparison ? [
    { type: "scatter", mode: "lines+markers", name: first?.player_name, x: comparison.aRows.map((row) => row.season), y: comparison.aRows.map((row) => toChartNumber(row[careerMetric])), connectgaps: false, line: { width: 3 } },
    { type: "scatter", mode: "lines+markers", name: second?.player_name, x: comparison.bRows.map((row) => row.season), y: comparison.bRows.map((row) => toChartNumber(row[careerMetric])), connectgaps: false, line: { width: 3 } },
  ] : [];
  const loading = firstQuery.isLoading || secondQuery.isLoading;
  const bothSelected = Boolean(first && second);

  return (
    <div className="page">
      <SectionTitle eyebrow="Head to Head" title="두 선수의 커리어를 비교하세요" description="두 선수에게 공통으로 존재하는 최신 시즌을 기준으로 비교합니다." />
      <div className="two-column" style={{ marginTop: 28 }}>
        <PlayerPicker label="PLAYER A" selected={first} onSelect={setFirst} />
        <PlayerPicker label="PLAYER B" selected={second} onSelect={setSecond} />
      </div>
      <div className="tabs" style={{ width: "fit-content", marginTop: 18 }}>
        <button className={role === "batting" ? "active" : ""} onClick={() => setRole("batting")}>타자</button>
        <button className={role === "pitching" ? "active" : ""} onClick={() => setRole("pitching")}>투수</button>
      </div>
      {loading ? <LoadingPanel /> : firstQuery.isError || secondQuery.isError ? (
        <ErrorPanel error={firstQuery.error ?? secondQuery.error} />
      ) : comparison ? (
        <section className="section two-column">
          <div className="panel">
            <div className="panel-header"><h2>{comparison.comparisonSeason} 시즌 능력치</h2><span className="muted">선수 간 상대 정규화</span></div>
            <RadarChart labels={comparison.metrics.map((metric) => metricLabels[metric])} players={[{ name: first!.player_name, values: comparison.aValues }, { name: second!.player_name, values: comparison.bValues }]} />
          </div>
          <div className="panel">
            <div className="panel-header"><h2>{role === "batting" ? "OPS" : "ERA"} 커리어</h2></div>
            <LineChart traces={lineTraces} height={430} />
          </div>
        </section>
      ) : (
        <div className="state-panel"><p>{bothSelected ? "선택한 역할에서 두 선수의 공통 시즌 기록이 없습니다." : "비교할 선수 두 명을 선택해 주세요."}</p></div>
      )}
    </div>
  );
}
