"use client";

import { MetricCard } from "@/components/ui";
import { formatMetric } from "@/lib/metrics";
import type { BattingSeason } from "@/types/api";

const metrics = [
  ["walk_percentage", "BB%", "타석당 볼넷 비율"],
  ["strikeout_percentage", "K%", "타석당 삼진 비율"],
  ["walk_to_strikeout_ratio", "BB/K", "삼진 1개당 볼넷"],
  ["isolated_power", "ISO", "장타율에서 타율을 뺀 순수 장타력"],
  ["batting_average_on_balls_in_play", "BABIP", "인플레이 타구의 안타 비율"],
  ["stolen_base_percentage", "SB%", "도루 시도 성공률"],
  ["speed_score", "Spd", "도루·3루타·득점을 결합한 0~10 주루 점수"],
  ["weighted_stolen_base_runs", "wSB", "리그 평균 대비 도루 득점 기여"],
  ["weighted_double_play_runs", "wGDP", "리그 평균 대비 병살 억제 득점 추정"],
  ["weighted_on_base_average", "wOBA", "출루 사건별 득점 가치를 반영한 출루율"],
  ["weighted_runs_above_average", "wRAA", "리그 평균 타자 대비 추가 득점"],
  ["weighted_runs_created", "wRC", "가중 득점 생산량"],
  ["weighted_runs_created_plus", "wRC+", "리그 평균 100 기준 공격 생산력"],
] as const;

export function OffenseDashboard({ rows }: { rows: BattingSeason[] }) {
  const ordered = [...rows].sort((a, b) => a.season - b.season);
  const latest = ordered.at(-1);
  if (!latest) return null;

  return (
    <section className="offense-dashboard">
      <div className="section-title defense-title">
        <span>ADVANCED BATTING METRICS</span>
        <h2>공격·주루 지표</h2>
        <p>기존 KBO 원시 기록과 같은 시즌 리그 기준값으로 계산했습니다.</p>
      </div>
      <div className="metric-grid advanced-metric-grid">
        {metrics.map(([key, label, description]) => (
          <MetricCard key={key} label={label} description={description} value={formatMetric(key, latest[key] as number | null)} hint={`${latest.season} ${latest.is_partial ? `${latest.as_of_date ?? ""} 기준` : "시즌"}`} />
        ))}
      </div>
      <section className="section panel">
        <div className="panel-header"><h2>시즌별 세이버 지표</h2><span className="muted">가로로 밀어 전체 지표 확인</span></div>
        <div className="table-wrap">
          <table className="data-table advanced-table">
            <thead><tr><th>시즌</th><th>팀</th>{metrics.map(([, label]) => <th key={label}>{label}</th>)}</tr></thead>
            <tbody>{[...ordered].reverse().map((row) => (
              <tr key={`${row.season}-${row.team}`}><td className="rank">{row.season}</td><td>{row.team}</td>{metrics.map(([key]) => <td key={key}>{formatMetric(key, row[key] as number | null)}</td>)}</tr>
            ))}</tbody>
          </table>
        </div>
      </section>
      <p className="ranking-notice metric-method-note">wOBA는 KBO 원자료에 고의4구가 없어 전체 볼넷을 사용합니다. wGDP는 인플레이 타구를 병살 기회로 본 추정값이며, wRC+는 구장 비보정 값입니다.</p>
    </section>
  );
}
