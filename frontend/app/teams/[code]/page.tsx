"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, UsersRound } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { ErrorPanel, LoadingPanel, MetricCard } from "@/components/ui";
import { api } from "@/lib/api";
import type { RosterMember } from "@/types/api";

const positions = [
  { value: "ALL", label: "전체" },
  { value: "P", label: "투수" },
  { value: "C", label: "포수" },
  { value: "IF", label: "내야수" },
  { value: "OF", label: "외야수" },
] as const;

function physical(member: RosterMember) {
  if (member.height_cm == null || member.weight_kg == null) return "정보 없음";
  return `${member.height_cm}cm · ${member.weight_kg}kg`;
}

export default function TeamRosterPage() {
  const { code } = useParams<{ code: string }>();
  const teamCode = code.toUpperCase();
  const [position, setPosition] = useState<(typeof positions)[number]["value"]>("ALL");
  const roster = useQuery({
    queryKey: ["team-roster", teamCode, 2026],
    queryFn: () => api.teamRoster(teamCode, 2026),
    enabled: teamCode.length === 2,
  });
  const members = useMemo(
    () => roster.data?.members.filter((member) => position === "ALL" || member.position === position) ?? [],
    [position, roster.data],
  );

  if (roster.isLoading) return <div className="page"><LoadingPanel label="로스터를 불러오고 있습니다" /></div>;
  if (roster.isError) return <div className="page"><ErrorPanel error={roster.error} /></div>;

  const team = roster.data?.team;
  return (
    <div className="page">
      <Link className="back-link" href="/teams"><ArrowLeft size={16} />구단 목록</Link>
      <header className="player-heading team-heading">
        <div>
          <span className="eyebrow">2026 ACTIVE ROSTER · {team?.as_of_date}</span>
          <h1>{team?.team_name}</h1>
          <p className="muted">KBO 공식 1군 선수 등록 현황</p>
        </div>
        <span className="team-mark large"><UsersRound size={28} /></span>
      </header>

      <section className="metric-grid">
        <MetricCard label="등록 선수" value={`${team?.roster_count ?? 0}명`} />
        <MetricCard label="투수" value={`${team?.pitcher_count ?? 0}명`} />
        <MetricCard label="야수" value={`${team?.hitter_count ?? 0}명`} />
        <MetricCard label="기준일" value={team?.as_of_date ?? "—"} />
      </section>

      <section className="panel section roster-panel">
        <div className="panel-header">
          <h2>선수 명단</h2>
          <div className="tabs">
            {positions.map((item) => (
              <button
                className={position === item.value ? "active" : ""}
                key={item.value}
                onClick={() => setPosition(item.value)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>등번호</th><th>선수</th><th>포지션</th><th>투타</th><th>생년월일</th><th>체격</th><th /></tr></thead>
            <tbody>
              {members.map((member) => (
                <tr key={member.player_id}>
                  <td className="rank">{member.uniform_number}</td>
                  <td><strong>{member.player_name}</strong></td>
                  <td><span className="badge">{member.position_label}</span></td>
                  <td>{member.throw_side} / {member.bat_side}</td>
                  <td>{member.birth_date} <span className="muted">({member.age}세)</span></td>
                  <td>{physical(member)}</td>
                  <td>
                    <Link
                      className="button ghost"
                      href={`/players/${member.player_id}?role=${member.position === "P" ? "pitching" : "batting"}`}
                    >
                      선수 분석
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
