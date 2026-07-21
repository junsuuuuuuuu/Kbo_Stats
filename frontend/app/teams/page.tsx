"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, UsersRound } from "lucide-react";
import Link from "next/link";

import { ErrorPanel, LoadingPanel, SectionTitle } from "@/components/ui";
import { api } from "@/lib/api";

export default function TeamsPage() {
  const teams = useQuery({
    queryKey: ["teams", 2026],
    queryFn: () => api.teams(2026),
  });

  return (
    <div className="page">
      <SectionTitle
        eyebrow="2026 Active Rosters"
        title="구단별 1군 로스터"
        description="KBO 공식 선수 등록 현황 기준입니다. 구단을 선택해 등록 선수를 확인하세요."
      />
      {teams.isLoading ? (
        <LoadingPanel label="구단 로스터를 불러오고 있습니다" />
      ) : teams.isError ? (
        <ErrorPanel error={teams.error} />
      ) : (
        <section className="feature-grid team-grid">
          {teams.data?.items.map((team) => (
            <Link className="feature-card team-card" href={`/teams/${team.team_code}`} key={team.team_code}>
              <div className="team-card-heading">
                <span className="team-mark">{team.team_name.slice(0, 2)}</span>
                <ArrowRight size={18} />
              </div>
              <h3>{team.team_name}</h3>
              <p><UsersRound size={15} /> 등록 선수 {team.roster_count}명</p>
              <div className="team-counts">
                <span>투수 {team.pitcher_count}</span>
                <span>야수 {team.hitter_count}</span>
              </div>
              <small>{team.as_of_date} 기준</small>
            </Link>
          ))}
        </section>
      )}
    </div>
  );
}
