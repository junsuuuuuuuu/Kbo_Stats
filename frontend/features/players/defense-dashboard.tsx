"use client";

import { MetricCard } from "@/components/ui";
import type { BattingSeason } from "@/types/api";

export function DefenseDashboard({ rows }: { rows: BattingSeason[] }) {
  const ordered = [...rows].sort((first, second) => first.season - second.season);
  const latest = ordered.at(-1);
  const derRows = ordered.filter((row) => row.defensive_efficiency != null);
  const bestDer = derRows.length
    ? Math.max(...derRows.map((row) => row.defensive_efficiency!))
    : null;
  const careerErrors = ordered.reduce((total, row) => total + row.errors, 0);
  return (
    <section className="defense-dashboard">
      <div className="section-title defense-title">
        <span>DEFENSIVE METRICS</span>
        <h2>수비 지표</h2>
        <p>개인 실책과 소속 팀의 인플레이 타구 처리 효율을 분리해서 보여줍니다.</p>
      </div>

      <div className="metric-grid defense-metric-grid">
        <MetricCard description="해당 시즌 소속 팀 전체의 수비 효율" hint={`${latest?.season ?? ""} ${latest?.team ?? ""}`} label="팀 DER" value={latest?.defensive_efficiency?.toFixed(3) ?? "—"} />
        <MetricCard description="해당 시즌 선수 개인 실책" hint={`${latest?.season ?? ""} 시즌`} label="개인 E" value={latest ? latest.errors.toLocaleString("ko-KR") : "—"} />
        <MetricCard description="보유한 전체 시즌 기록의 개인 실책 합계" hint="커리어 합계" label="통산 E" value={careerErrors.toLocaleString("ko-KR")} />
        <MetricCard description="선수가 속했던 팀의 시즌 DER 중 최고값" hint="소속 팀 기준" label="최고 팀 DER" value={bestDer?.toFixed(3) ?? "—"} />
      </div>

      <section className="section panel">
        <div className="panel-header"><h2>시즌별 수비 기록</h2><span className="muted">팀 DER과 개인 실책을 같은 행에서 비교</span></div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>시즌</th><th>팀</th><th>포지션</th><th>출장</th><th>개인 E</th><th>팀 DER</th><th>기준일 · 구단 순위</th></tr></thead>
            <tbody>
              {[...ordered].reverse().map((row) => (
                <tr key={`${row.season}-${row.team}`}>
                  <td className="rank">{row.season}</td><td>{row.team}</td><td>{row.position}</td>
                  <td>{row.games}</td><td><b>{row.errors}</b></td>
                  <td>{row.defensive_efficiency?.toFixed(3) ?? "—"}</td>
                  <td className="muted">
                    {row.is_partial ? row.as_of_date ?? "진행 중" : "시즌 최종"}
                    {row.team_rank != null ? ` · ${row.is_partial ? "현재 " : ""}${row.team_rank}위` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
