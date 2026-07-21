"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { DragScroll } from "@/components/drag-scroll";
import { TeamLogo } from "@/components/team-logo";
import { ErrorPanel, LoadingPanel } from "@/components/ui";
import { api } from "@/lib/api";
import type { GameTeamBox } from "@/types/api";

function HitterTable({ team }: { team: GameTeamBox }) {
  return <section className="section panel game-stat-panel">
    <div className="panel-header"><h2>{team.team_name} 타자 기록</h2><span className="muted">타석 결과 포함</span></div>
    <DragScroll className="boxscore-scroll"><table className="data-table boxscore-table hitter-boxscore">
      <thead><tr><th>타순</th><th>포지션</th><th>선수</th><th>AB</th><th>H</th><th>RBI</th><th>R</th><th>AVG</th><th>타석 결과</th></tr></thead>
      <tbody>{team.hitters.map((player, index) => <tr key={`${player.player_name}-${index}`}>
        <td className="rank">{player.batting_order}</td><td>{player.position}</td><td><strong>{player.player_name}</strong></td>
        <td>{player.at_bats}</td><td>{player.hits}</td><td>{player.runs_batted_in}</td><td>{player.runs}</td><td>{player.batting_average.toFixed(3)}</td>
        <td className="plate-result-list">{player.plate_appearances.map((result, atBat) => <span key={`${result}-${atBat}`}>{result}</span>)}</td>
      </tr>)}</tbody>
    </table></DragScroll>
  </section>;
}

function PitcherTable({ team }: { team: GameTeamBox }) {
  return <section className="section panel game-stat-panel">
    <div className="panel-header"><h2>{team.team_name} 투수 기록</h2><span className="muted">경기 등판 기록</span></div>
    <DragScroll className="boxscore-scroll"><table className="data-table boxscore-table pitcher-boxscore">
      <thead><tr><th>선수</th><th>등판</th><th>결과</th><th>W</th><th>L</th><th>SV</th><th>IP</th><th>BF</th><th>NP</th><th>AB</th><th>H</th><th>HR</th><th>BB+HBP</th><th>SO</th><th>R</th><th>ER</th><th>ERA</th></tr></thead>
      <tbody>{team.pitchers.map((player) => <tr key={player.player_name}>
        <td><strong>{player.player_name}</strong></td><td>{player.appearance}</td><td>{player.result ?? "—"}</td>
        <td>{player.wins}</td><td>{player.losses}</td><td>{player.saves}</td><td>{player.innings_pitched}</td><td>{player.batters_faced}</td><td>{player.pitches}</td><td>{player.at_bats}</td><td>{player.hits_allowed}</td><td>{player.home_runs_allowed}</td><td>{player.walks_and_hit_batters}</td><td>{player.strikeouts}</td><td>{player.runs_allowed}</td><td>{player.earned_runs}</td><td>{player.earned_run_average.toFixed(2)}</td>
      </tr>)}</tbody>
    </table></DragScroll>
  </section>;
}

export default function TeamGameDetailPage() {
  const { code, gameId } = useParams<{ code: string; gameId: string }>();
  const teamCode = code.toUpperCase();
  const game = useQuery({ queryKey: ["team-game", teamCode, gameId], queryFn: () => api.teamGame(teamCode, gameId), enabled: Boolean(gameId) });
  if (game.isLoading) return <div className="page"><LoadingPanel label="경기 상세 기록을 불러오고 있습니다" /></div>;
  if (game.isError || !game.data) return <div className="page"><ErrorPanel error={game.error} /></div>;
  const data = game.data;
  const innings = Array.from({ length: Math.max(data.away.innings.length, data.home.innings.length) }, (_, index) => index + 1);

  return <div className="page game-detail-page">
    <Link className="back-link" href={`/teams/${teamCode}`}><ArrowLeft size={16} />구단 상세로 돌아가기</Link>
    <section className="game-score-hero panel">
      <div className="game-score-team"><TeamLogo teamCode={data.away.team_code} teamName={data.away.team_name} /><strong>{data.away.team_name}</strong><b>{data.away.runs}</b></div>
      <div className="game-score-meta"><span className="badge">경기 종료</span><strong>{data.game_date}</strong><small>{data.stadium} · {data.start_time}–{data.end_time} · {data.duration}</small></div>
      <div className="game-score-team home"><b>{data.home.runs}</b><strong>{data.home.team_name}</strong><TeamLogo teamCode={data.home.team_code} teamName={data.home.team_name} /></div>
    </section>

    <section className="section panel inning-panel"><DragScroll className="boxscore-scroll"><table className="data-table inning-table">
      <thead><tr><th>팀</th>{innings.map((inning) => <th key={inning}>{inning}</th>)}<th>R</th><th>H</th><th>E</th><th>B</th></tr></thead>
      <tbody>{[data.away, data.home].map((team) => <tr key={team.team_code}><td><strong>{team.team_name}</strong></td>{innings.map((_, index) => <td key={index}>{team.innings[index] ?? "-"}</td>)}<td className="primary-stat">{team.runs}</td><td>{team.hits}</td><td>{team.errors}</td><td>{team.walks}</td></tr>)}</tbody>
    </table></DragScroll></section>

    {data.key_events.length ? <section className="section panel game-events"><div className="panel-header"><h2>주요 기록</h2><span className="muted">결승타·장타·도루·실책 등</span></div><dl>{data.key_events.map(([label, value], index) => <div key={`${label}-${index}`}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section> : null}
    <HitterTable team={data.away} /><PitcherTable team={data.away} />
    <HitterTable team={data.home} /><PitcherTable team={data.home} />
    <a className="appearance-source game-detail-source" href={data.source_url} rel="noreferrer" target="_blank">KBO 공식 게임센터 <ArrowUpRight size={13} /></a>
  </div>;
}
