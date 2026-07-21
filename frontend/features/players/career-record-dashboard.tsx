"use client";

import { useMemo, useState } from "react";

import { MetricCard } from "@/components/ui";
import { formatMetric } from "@/lib/metrics";
import type { AnalyticsRole, BattingSeason, PitchingSeason } from "@/types/api";

type CareerSeason = BattingSeason | PitchingSeason;

interface MetricDefinition {
  key: string;
  label: string;
}

const battingCards: MetricDefinition[] = [
  { key: "games", label: "G" },
  { key: "plate_appearances", label: "PA" },
  { key: "batting_average", label: "AVG" },
  { key: "on_base_plus_slugging", label: "OPS" },
  { key: "home_runs", label: "HR" },
  { key: "runs_batted_in", label: "RBI" },
  { key: "stolen_bases", label: "SB" },
  { key: "walks", label: "BB" },
];

const battingColumns: MetricDefinition[] = [
  { key: "games", label: "G" },
  { key: "plate_appearances", label: "PA" },
  { key: "at_bats", label: "AB" },
  { key: "hits", label: "H" },
  { key: "doubles", label: "2B" },
  { key: "triples", label: "3B" },
  { key: "home_runs", label: "HR" },
  { key: "runs", label: "R" },
  { key: "runs_batted_in", label: "RBI" },
  { key: "stolen_bases", label: "SB" },
  { key: "walks", label: "BB" },
  { key: "strikeouts", label: "SO" },
  { key: "batting_average", label: "AVG" },
  { key: "on_base_percentage", label: "OBP" },
  { key: "slugging_percentage", label: "SLG" },
  { key: "on_base_plus_slugging", label: "OPS" },
];

const pitchingCards: MetricDefinition[] = [
  { key: "games", label: "G" },
  { key: "innings_pitched", label: "IP" },
  { key: "earned_run_average", label: "ERA" },
  { key: "strikeouts", label: "SO" },
  { key: "wins", label: "W" },
  { key: "losses", label: "L" },
  { key: "saves", label: "SV" },
  { key: "holds", label: "HLD" },
];

const pitchingColumns: MetricDefinition[] = [
  { key: "games", label: "G" },
  { key: "wins", label: "W" },
  { key: "losses", label: "L" },
  { key: "saves", label: "SV" },
  { key: "holds", label: "HLD" },
  { key: "innings_pitched", label: "IP" },
  { key: "earned_run_average", label: "ERA" },
  { key: "batters_faced", label: "BF" },
  { key: "hits_allowed", label: "H" },
  { key: "home_runs_allowed", label: "HR" },
  { key: "walks_allowed", label: "BB" },
  { key: "hit_batters", label: "HBP" },
  { key: "strikeouts", label: "SO" },
  { key: "runs_allowed", label: "R" },
  { key: "earned_runs", label: "ER" },
  { key: "winning_percentage", label: "WPCT" },
];

const battingDescriptions: Readonly<Record<string, string>> = {
  games: "출장 경기 수",
  plate_appearances: "타석 수",
  at_bats: "타수",
  runs: "득점",
  hits: "안타",
  doubles: "2루타",
  triples: "3루타",
  home_runs: "홈런",
  runs_batted_in: "타점",
  stolen_bases: "도루",
  walks: "볼넷",
  strikeouts: "삼진",
  batting_average: "타율",
  on_base_percentage: "출루율",
  slugging_percentage: "장타율",
  on_base_plus_slugging: "출루율과 장타율의 합",
};

const pitchingDescriptions: Readonly<Record<string, string>> = {
  games: "등판 경기 수",
  wins: "승리",
  losses: "패전",
  saves: "세이브",
  holds: "홀드",
  innings_pitched: "투구 이닝",
  earned_run_average: "평균자책점",
  batters_faced: "상대한 타자 수",
  hits_allowed: "피안타",
  home_runs_allowed: "피홈런",
  walks_allowed: "허용 볼넷",
  hit_batters: "몸에 맞는 공 허용",
  strikeouts: "탈삼진",
  runs_allowed: "실점",
  earned_runs: "자책점",
  winning_percentage: "승률",
};

const rateMetrics = new Set([
  "batting_average",
  "on_base_percentage",
  "slugging_percentage",
  "on_base_plus_slugging",
  "earned_run_average",
  "winning_percentage",
]);

function metricValue(row: CareerSeason, key: string): string {
  const value = row[key];
  if (value == null) return "—";
  if (key === "innings_pitched") return String(value);
  if (typeof value !== "number") return String(value);
  if (rateMetrics.has(key)) return formatMetric(key, value);
  return value.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
}

function metricDescription(role: AnalyticsRole, key: string): string {
  const descriptions = role === "batting" ? battingDescriptions : pitchingDescriptions;
  return descriptions[key] ?? key;
}

interface CareerRecordDashboardProps {
  role: AnalyticsRole;
  rows: CareerSeason[];
}

export function CareerRecordDashboard({ role, rows }: CareerRecordDashboardProps) {
  const orderedRows = useMemo(
    () => [...rows].sort((first, second) => first.season - second.season),
    [rows],
  );
  const [selectedSeason, setSelectedSeason] = useState(
    () => orderedRows.at(-1)?.season ?? 0,
  );
  const selected = orderedRows.find((row) => row.season === selectedSeason);
  const cards = role === "batting" ? battingCards : pitchingCards;
  const columns = role === "batting" ? battingColumns : pitchingColumns;

  if (!selected) return null;

  return (
    <section className="section panel career-dashboard">
      <div className="panel-header career-dashboard-header">
        <div>
          <span className="eyebrow">SEASON BY SEASON</span>
          <h2>연도별 커리어 기록</h2>
          <p className="muted">
            {selected.team} · {selected.age}세
            {selected.is_partial && selected.as_of_date
              ? ` · ${selected.as_of_date} 기준 진행 중`
              : " · 정규시즌 최종"}
          </p>
        </div>
        <label className="season-picker">
          <span>시즌</span>
          <select
            onChange={(event) => setSelectedSeason(Number(event.target.value))}
            value={selectedSeason}
          >
            {[...orderedRows].reverse().map((row) => (
              <option key={row.season} value={row.season}>
                {row.season}{row.is_partial ? " (진행 중)" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="metric-grid career-metric-grid">
        {cards.map((metric) => (
          <MetricCard
            description={metricDescription(role, metric.key)}
            hint={`${selected.season} ${selected.team}`}
            key={metric.key}
            label={metric.label}
            value={metricValue(selected, metric.key)}
          />
        ))}
      </div>

      <div className="table-wrap career-table-wrap">
        <table className="data-table career-table">
          <thead>
            <tr>
              <th>시즌</th>
              <th>팀</th>
              <th>나이</th>
              {columns.map((column) => {
                const description = metricDescription(role, column.key);
                return (
                  <th key={column.key}>
                    <abbr
                      aria-label={`${column.label}: ${description}`}
                      className="stat-abbreviation"
                      data-tooltip={description}
                      tabIndex={0}
                      title={description}
                    >
                      {column.label}
                    </abbr>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {[...orderedRows].reverse().map((row) => (
              <tr className={row.season === selectedSeason ? "selected" : ""} key={row.season}>
                <td>
                  <button
                    className="career-season-button"
                    onClick={() => setSelectedSeason(row.season)}
                    type="button"
                  >
                    {row.season}
                  </button>
                  {row.is_partial ? <span className="badge">진행 중</span> : null}
                </td>
                <td>{row.team}</td>
                <td>{row.age}</td>
                {columns.map((column) => (
                  <td key={column.key}>{metricValue(row, column.key)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
