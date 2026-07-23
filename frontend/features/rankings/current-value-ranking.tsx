"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { RankingTable } from "@/features/rankings/ranking-table";
import { CURRENT_SEASON } from "@/lib/constants";
import type { AnalyticsRole, RankingValueType } from "@/types/api";

export function CurrentValueRanking() {
  const [role, setRole] = useState<AnalyticsRole>("batting");
  const [valueType, setValueType] = useState<RankingValueType>("overall");
  const title = role === "pitching" ? "현재 시즌 투수 가치 TOP 5" : `현재 시즌 타자 ${valueType === "offense" ? "공격" : valueType === "defense" ? "수비" : "종합"} 가치 TOP 5`;

  return <div className="panel">
    <div className="panel-header current-ranking-header">
      <div><span className="eyebrow">{CURRENT_SEASON} CURRENT VALUE RANKING</span><h2>{title}</h2></div>
      <Link className="button ghost" href="/rankings">전체 보기<ArrowRight size={16} /></Link>
    </div>
    <div className="ranking-mode-controls">
      <div className="tabs"><button className={role === "batting" ? "active" : ""} onClick={() => setRole("batting")}>타자</button><button className={role === "pitching" ? "active" : ""} onClick={() => { setRole("pitching"); setValueType("overall"); }}>투수</button></div>
      {role === "batting" ? <div className="tabs"><button className={valueType === "overall" ? "active" : ""} onClick={() => setValueType("overall")}>종합</button><button className={valueType === "offense" ? "active" : ""} onClick={() => setValueType("offense")}>공격</button><button className={valueType === "defense" ? "active" : ""} onClick={() => setValueType("defense")}>수비</button></div> : null}
    </div>
    <RankingTable role={role} season={CURRENT_SEASON} limit={5} valueType={valueType} />
  </div>;
}
