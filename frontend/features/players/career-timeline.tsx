import type { AnalyticsRole, BattingSeason, PitchingSeason } from "@/types/api";
import { formatMetric } from "@/lib/metrics";

type CareerSeason = BattingSeason | PitchingSeason;

const metricLabels = {
  on_base_plus_slugging: "OPS",
  earned_run_average: "ERA",
};

export function CareerTimeline({ role, rows }: { role: AnalyticsRole; rows: CareerSeason[] }) {
  if (!rows.length) return null;
  const metric = role === "batting" ? "on_base_plus_slugging" : "earned_run_average";
  const values = rows.map((row) => Number(row[metric])).filter(Number.isFinite);
  const bestValue = role === "batting" ? Math.max(...values) : Math.min(...values);

  return (
    <section className="section timeline-section">
      <div className="panel-header timeline-heading">
        <div><span className="eyebrow">CAREER MOMENTS</span><h2>커리어 타임라인</h2></div>
        <p className="muted">데뷔부터 이적, 커리어 하이와 최근 시즌까지</p>
      </div>
      <div className="career-timeline">
        {rows.map((row, index) => {
          const value = Number(row[metric]);
          const previous = rows[index - 1];
          const tags = [
            index === 0 ? "데뷔" : null,
            previous && previous.team !== row.team ? `${row.team} 이적` : null,
            Number.isFinite(value) && value === bestValue ? "커리어 하이" : null,
            index === rows.length - 1 ? (row.is_partial ? "진행 중" : "최근 시즌") : null,
          ].filter(Boolean);
          return (
            <article className="timeline-item" key={`${row.season}-${row.team}`}>
              <span className="timeline-dot" />
              <strong>{row.season}</strong>
              <span className="timeline-team">{row.team} · {row.age}세</span>
              <b>{metricLabels[metric]} {formatMetric(metric, value)}</b>
              <div className="timeline-tags">{tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
