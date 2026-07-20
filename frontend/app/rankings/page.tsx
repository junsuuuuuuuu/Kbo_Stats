"use client";

import { Trophy } from "lucide-react";
import { useState } from "react";

import { SectionTitle } from "@/components/ui";
import { RankingTable } from "@/features/rankings/ranking-table";
import type { AnalyticsRole } from "@/types/api";

export default function RankingsPage() {
  const [role, setRole] = useState<AnalyticsRole>("batting");
  return <div className="page"><div className="player-heading"><SectionTitle eyebrow="Explainable AI Score" title="2025 선수 가치 랭킹" description="같은 시즌 안에서 공격·꾸준함·출장·나이·팀 기여를 0~100으로 평가합니다." /><Trophy size={42} color="var(--accent)" /></div><div className="panel"><div className="panel-header"><div className="tabs"><button className={role === "batting" ? "active" : ""} onClick={() => setRole("batting")}>타자</button><button className={role === "pitching" ? "active" : ""} onClick={() => setRole("pitching")}>투수</button></div><span className="muted">최소 타자 100 PA · 투수 30 IP</span></div><RankingTable role={role} limit={50} /></div></div>;
}
