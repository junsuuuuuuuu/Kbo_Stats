import { AlertCircle, LoaderCircle } from "lucide-react";

export function SectionTitle({ eyebrow, title, description }: { eyebrow?: string; title: string; description?: string }) {
  return <div className="section-title">{eyebrow && <span>{eyebrow}</span>}<h2>{title}</h2>{description && <p>{description}</p>}</div>;
}

export function LoadingPanel({ label = "데이터를 분석하고 있습니다" }: { label?: string }) {
  return <div className="state-panel"><LoaderCircle className="spin" /><p>{label}</p></div>;
}

export function ErrorPanel({ error }: { error: unknown }) {
  return <div className="state-panel error"><AlertCircle /><p>{error instanceof Error ? error.message : "오류가 발생했습니다."}</p></div>;
}

export function ScoreBar({ label, value }: { label: string; value: number }) {
  return <div className="score-row"><div><span>{label.replaceAll("_", " ")}</span><b>{value.toFixed(1)}</b></div><div className="score-track"><i style={{ width: `${Math.min(100, value)}%` }} /></div></div>;
}

export function MetricCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return <div className="metric-card"><span>{label}</span><strong>{value}</strong>{hint && <small>{hint}</small>}</div>;
}
