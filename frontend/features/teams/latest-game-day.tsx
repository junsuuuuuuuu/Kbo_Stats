"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { DragScroll } from "@/components/drag-scroll";
import { ErrorPanel, LoadingPanel, SectionTitle } from "@/components/ui";
import { api } from "@/lib/api";
import { CURRENT_SEASON } from "@/lib/constants";
import type { GameDayStar, LatestGameSummary } from "@/types/api";

function Ace({ hitter, pitcher }: { hitter: GameDayStar; pitcher: GameDayStar }) {
  return <div className="daily-aces">
    <span><i>타</i><b>{hitter.player_name}</b><small>{hitter.summary}</small></span>
    <span><i>투</i><b>{pitcher.player_name}</b><small>{pitcher.summary}</small></span>
  </div>;
}

function Matchup({ game }: { game: LatestGameSummary }) {
  const content = <>
    <span>{game.away.team_name}</span>
    <strong>{game.status === "completed" ? `${game.away.runs} : ${game.home.runs}` : "VS"}</strong>
    <span>{game.home.team_name}</span>
    <small className={`daily-decision ${game.status === "cancelled" ? "cancelled" : ""}`}>
      {game.status === "cancelled" ? (game.cancellation_reason ?? "경기 취소")
        : game.status === "scheduled" ? "경기 예정"
        : game.winning_pitcher && game.losing_pitcher
          ? <><b>승</b> {game.winning_pitcher}<i>·</i><b>패</b> {game.losing_pitcher}</>
          : "승·패 투수 없음"}
    </small>
  </>;
  return game.status === "completed"
    ? <Link className="daily-matchup" href={`/teams/${game.away.team_code}/games/${game.game_id}`} rel="noreferrer" target="_blank">{content}</Link>
    : <div className="daily-matchup">{content}</div>;
}

function adjacentDate(value: string, offset: number) {
  const [year, month, day] = value.split("-").map(Number);
  const next = new Date(year, month - 1, day + offset);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}-${String(next.getDate()).padStart(2, "0")}`;
}

function dateWithWeekday(value: string) {
  const weekdays = ["일", "월", "화", "수", "목", "금", "토"];
  const [year, month, day] = value.split("-").map(Number);
  const weekday = weekdays[new Date(year, month - 1, day).getDay()];
  return `${value} (${weekday})`;
}

export function LatestGameDayTable() {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const latest = useQuery({
    queryKey: ["game-day", selectedDate ?? "latest", CURRENT_SEASON],
    queryFn: () => selectedDate ? api.gamesByDay(selectedDate, CURRENT_SEASON) : api.latestGames(CURRENT_SEASON),
  });
  const showAces = latest.data?.games.some((game) => game.away_hitter || game.home_hitter) ?? false;

  return <section className="section latest-games-section">
    <SectionTitle
      eyebrow="Latest KBO Results"
      title="가장 최근 경기 결과"
      description="가장 최근 종료된 경기일의 전체 결과와 구단별 당일 대표 타자·투수를 보여줍니다."
    />
    {latest.isLoading ? <LoadingPanel label="최근 경기 결과를 불러오고 있습니다" />
      : latest.isError || !latest.data ? <ErrorPanel error={latest.error} />
      : <div className="panel latest-games-panel">
        <div className="latest-games-heading">
          <button aria-label="전날 경기" className="game-day-arrow" onClick={() => setSelectedDate(adjacentDate(latest.data.game_date, -1))} type="button"><ChevronLeft /></button>
          <div><span className="eyebrow">GAME DAY</span><h2>{dateWithWeekday(latest.data.game_date)}</h2></div>
          <span className="muted">{latest.data.games.length ? `총 ${latest.data.games.length}경기` : "경기 없음"}</span>
          <button aria-label="다음날 경기" className="game-day-arrow" onClick={() => setSelectedDate(adjacentDate(latest.data.game_date, 1))} type="button"><ChevronRight /></button>
        </div>
        {!latest.data.games.length ? <div className="game-day-empty"><strong>예정된 경기가 없습니다</strong><span>화살표를 눌러 다른 날짜의 경기와 일정을 확인하세요.</span></div> : <DragScroll className="latest-games-scroll">
          {showAces ? <table className="data-table latest-games-table">
            <thead><tr><th>시간</th><th>경기 결과</th><th>구장</th><th>원정팀 대표 선수</th><th>홈팀 대표 선수</th></tr></thead>
            <tbody>{latest.data.games.map((game) => <tr key={game.game_id}>
              <td>{game.start_time}</td><td><Matchup game={game} /></td><td>{game.stadium}</td>
              <td>{game.away_hitter && game.away_pitcher ? <Ace hitter={game.away_hitter} pitcher={game.away_pitcher} /> : <span className="daily-pending">경기 취소</span>}</td>
              <td>{game.home_hitter && game.home_pitcher ? <Ace hitter={game.home_hitter} pitcher={game.home_pitcher} /> : <span className="daily-pending">경기 취소</span>}</td>
            </tr>)}</tbody>
          </table> : <table className="data-table latest-games-table schedule-only">
            <thead><tr><th>시간</th><th>원정</th><th aria-label="대결" /><th>홈</th><th>구장</th></tr></thead>
            <tbody>{latest.data.games.map((game) => <tr key={game.game_id}>
              <td>{game.start_time}</td>
              <td><div className="schedule-team away"><strong>{game.away.team_name}</strong><small>선발 {game.away_starting_pitcher ?? "미정"}</small></div></td>
              <td><strong className={`schedule-versus ${game.status === "cancelled" ? "cancelled" : ""}`}>{game.status === "cancelled" ? "우취" : "VS"}</strong></td>
              <td><div className="schedule-team home"><strong>{game.home.team_name}</strong><small>선발 {game.home_starting_pitcher ?? "미정"}</small></div></td>
              <td><strong>{game.stadium}</strong></td>
            </tr>)}</tbody>
          </table>}
        </DragScroll>}
        <a className="appearance-source" href={latest.data.source_url} rel="noreferrer" target="_blank">KBO 공식 일정·결과 <ArrowUpRight size={13} /></a>
      </div>}
  </section>;
}
