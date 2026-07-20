"use client";

import { useQuery } from "@tanstack/react-query";
import { SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ErrorPanel, LoadingPanel, SectionTitle } from "@/components/ui";
import { api } from "@/lib/api";
import { buildDiscoveryParams } from "@/lib/analytics";
import type { AnalyticsRole } from "@/types/api";

export default function DiscoverPage() {
  const [role, setRole] = useState<AnalyticsRole>("batting");
  const [form, setForm] = useState({ max_age: "25", min_ops: "0.8", min_obp: "", min_slg: "", min_home_runs: "", max_era: "4.0", min_strikeouts: "50" });
  const [submitted, setSubmitted] = useState<Record<string, string | number | undefined>>({ role, season: 2025, max_age: 25, min_ops: .8 });
  const query = useQuery({ queryKey: ["discover", submitted], queryFn: () => api.discover(submitted) });
  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitted(buildDiscoveryParams(role, form));
  };
  return <div className="page"><SectionTitle eyebrow="AI Scouting" title="조건으로 숨은 선수를 찾으세요" description="충분한 시즌 표본을 가진 선수만 비교해 작은 표본의 착시를 줄였습니다." /><form className="panel" style={{ marginTop: 28 }} onSubmit={submit}><div className="panel-header"><div className="tabs"><button type="button" className={role === "batting" ? "active" : ""} onClick={() => setRole("batting")}>타자</button><button type="button" className={role === "pitching" ? "active" : ""} onClick={() => setRole("pitching")}>투수</button></div><SlidersHorizontal /></div><div className="form-grid"><div className="field"><label>최대 나이</label><input type="number" value={form.max_age} onChange={(e) => update("max_age", e.target.value)} /></div>{role === "batting" ? <><div className="field"><label>최소 OPS</label><input type="number" step="0.01" value={form.min_ops} onChange={(e) => update("min_ops", e.target.value)} /></div><div className="field"><label>최소 출루율</label><input type="number" step="0.01" value={form.min_obp} onChange={(e) => update("min_obp", e.target.value)} /></div><div className="field"><label>최소 홈런</label><input type="number" value={form.min_home_runs} onChange={(e) => update("min_home_runs", e.target.value)} /></div></> : <><div className="field"><label>최대 ERA</label><input type="number" step="0.1" value={form.max_era} onChange={(e) => update("max_era", e.target.value)} /></div><div className="field"><label>최소 탈삼진</label><input type="number" value={form.min_strikeouts} onChange={(e) => update("min_strikeouts", e.target.value)} /></div></>}</div><button className="button" style={{ marginTop: 20 }} type="submit">조건 검색</button></form><section className="panel" style={{ marginTop: 18 }}>{query.isLoading ? <LoadingPanel /> : query.isError ? <ErrorPanel error={query.error} /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>선수</th><th>팀</th><th>나이</th><th>{role === "batting" ? "OPS" : "ERA"}</th><th>{role === "batting" ? "HR" : "SO"}</th><th /></tr></thead><tbody>{query.data?.items.map((item) => <tr key={item.player_id}><td><strong>{item.player_name}</strong></td><td>{item.team}</td><td>{item.age}</td><td className="score">{Number(item.stats[role === "batting" ? "on_base_plus_slugging" : "earned_run_average"]).toFixed(3)}</td><td>{item.stats[role === "batting" ? "home_runs" : "strikeouts"]}</td><td><Link className="button ghost" href={`/players/${item.player_id}?role=${role}`}>분석</Link></td></tr>)}</tbody></table>{query.data?.items.length === 0 && <div className="state-panel"><p>조건에 맞는 선수가 없습니다.</p></div>}</div>}</section></div>;
}
