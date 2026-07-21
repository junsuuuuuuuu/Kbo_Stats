"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowUpRight, Trophy } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { TeamLogo } from "@/components/team-logo";
import { ErrorPanel, LoadingPanel, MetricCard } from "@/components/ui";
import { api } from "@/lib/api";
import { TeamGameResultTable } from "@/features/teams/team-game-results";
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
  const standing = useQuery({
    queryKey: ["team-standing", teamCode, 2026],
    queryFn: () => api.teamStanding(teamCode, 2026),
    enabled: teamCode.length === 2,
  });
  const games = useQuery({
    queryKey: ["team-games", teamCode, 2026],
    queryFn: () => api.teamGames(teamCode, 2026),
    enabled: teamCode.length === 2,
  });
  const teamName = roster.data?.team.team_name;
  const battingLeaders = useQuery({
    queryKey: ["team-leaders", "batting", teamName, 2026],
    queryFn: () => api.rankings("batting", 2026, teamName, 5),
    enabled: Boolean(teamName),
  });
  const pitchingLeaders = useQuery({
    queryKey: ["team-leaders", "pitching", teamName, 2026],
    queryFn: () => api.rankings("pitching", 2026, teamName, 5),
    enabled: Boolean(teamName),
  });
  const members = useMemo(
    () => roster.data?.members.filter((member) => position === "ALL" || member.position === position) ?? [],
    [position, roster.data],
  );

  if (roster.isLoading) return <div className="page"><LoadingPanel label="로스터를 불러오고 있습니다" /></div>;
  if (roster.isError) return <div className="page"><ErrorPanel error={roster.error} /></div>;

  const team = roster.data?.team;
  const record = standing.data;
  const ageGroups = members.reduce(
    (groups, member) => {
      if (member.age <= 23) groups.young += 1;
      else if (member.age <= 27) groups.developing += 1;
      else if (member.age <= 31) groups.prime += 1;
      else groups.veteran += 1;
      return groups;
    },
    { young: 0, developing: 0, prime: 0, veteran: 0 },
  );
  return (
    <div className="page">
      <Link className="back-link" href="/teams"><ArrowLeft size={16} />구단 목록</Link>
      <header className="player-heading team-heading">
        <div>
          <span className="eyebrow">2026 ACTIVE ROSTER · {team?.as_of_date}</span>
          <h1>{team?.team_name}</h1>
          <p className="muted">KBO 공식 1군 선수 등록 현황</p>
        </div>
        {team ? (
          <TeamLogo teamCode={team.team_code} teamName={team.team_name} size="large" />
        ) : null}
      </header>

      <section className="metric-grid team-standing-grid">
        <MetricCard label="현재 순위" value={record ? `${record.ranking}위` : "—"} hint={record ? `${record.games_behind}경기 차` : "전적 수집 전"} />
        <MetricCard label="시즌 전적" value={record ? `${record.wins}승 ${record.losses}패` : "—"} hint={record ? `${record.draws}무 · ${record.games}경기` : undefined} />
        <MetricCard label="승률" value={record ? record.winning_percentage.toFixed(3) : "—"} hint={record?.streak} />
        <MetricCard label="최근 10경기" value={record?.recent_ten ?? "—"} hint={record ? `${record.as_of_date} 기준` : undefined} />
      </section>

      {record ? <div className="team-split-record"><span>홈 <b>{record.home_record}</b></span><span>원정 <b>{record.away_record}</b></span><a href={record.source_url} target="_blank" rel="noreferrer">KBO 공식 전적 <ArrowUpRight size={14} /></a></div> : null}

      <TeamGameResultTable teamCode={teamCode} data={games.data} error={games.error} isError={games.isError} isLoading={games.isLoading} />

      <section className="section two-column team-dashboard-grid">
        {([
          ["타자 가치 리더", battingLeaders.data?.items ?? [], "batting"],
          ["투수 가치 리더", pitchingLeaders.data?.items ?? [], "pitching"],
        ] as const).map(([title, leaders, leaderRole]) => (
          <div className="panel" key={title}>
            <div className="panel-header"><h2>{title}</h2><Trophy size={19} /></div>
            {leaders.length ? <ol className="team-leader-list">{leaders.map((leader) => <li key={leader.player_id}><span>#{leader.team_rank}</span><Link href={`/players/${leader.player_id}?role=${leaderRole}`}><strong>{leader.player_name}</strong><small>{leader.reasons[0]}</small></Link><b>{leader.ai_score.toFixed(1)}</b></li>)}</ol> : <div className="state-panel"><p>집계 가능한 시즌 기록이 없습니다.</p></div>}
          </div>
        ))}
      </section>

      <section className="section panel roster-composition">
        <div className="panel-header"><div><span className="eyebrow">ROSTER COMPOSITION</span><h2>선수층 구성</h2></div><span className="muted">등록 선수 {team?.roster_count ?? 0}명</span></div>
        <div className="age-distribution">
          {[
            ["23세 이하", ageGroups.young], ["24–27세", ageGroups.developing],
            ["28–31세", ageGroups.prime], ["32세 이상", ageGroups.veteran],
          ].map(([label, count]) => <div key={label}><span>{label}</span><i style={{ height: `${Math.max(8, Number(count) / Math.max(members.length, 1) * 150)}px` }} /><strong>{count}명</strong></div>)}
        </div>
        <div className="roster-summary"><span>투수 <b>{team?.pitcher_count ?? 0}</b></span><span>야수 <b>{team?.hitter_count ?? 0}</b></span><span>기준일 <b>{team?.as_of_date ?? "—"}</b></span></div>
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
