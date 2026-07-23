"use client";

import { Trophy } from "lucide-react";
import { useState } from "react";

import { SectionTitle } from "@/components/ui";
import { RankingTable } from "@/features/rankings/ranking-table";
import { CURRENT_SEASON, LAST_COMPLETE_SEASON } from "@/lib/constants";
import type { AnalyticsRole, RankingValueType } from "@/types/api";

const RANKING_SEASONS = [2020, 2021, 2022, 2023, 2024, LAST_COMPLETE_SEASON, CURRENT_SEASON] as const;

export default function RankingsPage() {
  const [role, setRole] = useState<AnalyticsRole>("batting");
  const [season, setSeason] = useState<number>(CURRENT_SEASON);
  const [valueType, setValueType] = useState<RankingValueType>("overall");
  const isCurrentSeason = season === CURRENT_SEASON;

  return (
    <div className="page">
      <div className="player-heading">
        <SectionTitle
          eyebrow="Explainable AI Score"
          title={`${season} 선수 가치 랭킹`}
          description="같은 시즌 안에서 공격·꾸준함·출장·나이·팀 기여를 0~100으로 평가합니다."
        />
        <Trophy size={42} color="var(--accent)" />
      </div>

      <div className="panel">
        <div className="ranking-controls">
          <div className="tabs" aria-label="시즌 선택">
            {RANKING_SEASONS.map((year) => (
              <button
                key={year}
                className={season === year ? "active" : ""}
                onClick={() => setSeason(year)}
                type="button"
              >
                {year}
              </button>
            ))}
          </div>

          <div className="tabs" aria-label="선수 유형 선택">
            <button
              className={role === "batting" ? "active" : ""}
              onClick={() => setRole("batting")}
              type="button"
            >
              타자
            </button>
            <button
              className={role === "pitching" ? "active" : ""}
              onClick={() => { setRole("pitching"); setValueType("overall"); }}
              type="button"
            >
              투수
            </button>
          </div>
        </div>

        {role === "batting" ? <div className="value-type-tabs tabs" aria-label="타자 가치 구분">
          <button className={valueType === "overall" ? "active" : ""} onClick={() => setValueType("overall")} type="button">종합</button>
          <button className={valueType === "offense" ? "active" : ""} onClick={() => setValueType("offense")} type="button">공격</button>
          <button className={valueType === "defense" ? "active" : ""} onClick={() => setValueType("defense")} type="button">수비</button>
        </div> : null}

        <p className="ranking-notice">
          {isCurrentSeason
            ? `${CURRENT_SEASON} 랭킹은 최신 수집일 기준 진행 중 기록입니다. 시즌 종료 후 점수가 달라질 수 있습니다.`
            : `${season} 정규시즌 기록 기준입니다.`}
          {" · "}최소 타자 100 PA · 투수 30 IP
        </p>

        <RankingTable role={role} season={season} limit={50} valueType={valueType} />
      </div>
    </div>
  );
}
