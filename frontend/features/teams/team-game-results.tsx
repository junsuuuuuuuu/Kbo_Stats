"use client";

import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { DragScroll } from "@/components/drag-scroll";
import { ErrorPanel, LoadingPanel } from "@/components/ui";
import type { TeamGameResults } from "@/types/api";

const resultLabels = { W: "승", L: "패", D: "무" } as const;

interface TeamGameResultsProps {
  teamCode: string;
  data?: TeamGameResults;
  error: Error | null;
  isError: boolean;
  isLoading: boolean;
}

export function TeamGameResultTable({ teamCode, data, error, isError, isLoading }: TeamGameResultsProps) {
  return (
    <section className="section panel team-game-panel">
      <div className="panel-header">
        <div><span className="eyebrow">2026 GAME BY GAME</span><h2>날짜별 승·패 기록</h2></div>
        <span className="muted">끌어서 전체 경기 확인</span>
      </div>
      {isLoading ? <LoadingPanel label="구단 경기 결과를 불러오고 있습니다" /> : isError ? <ErrorPanel error={error} /> : !data?.items.length ? (
        <div className="state-panel"><p>완료된 정규시즌 경기가 없습니다.</p></div>
      ) : (
        <>
          <DragScroll className="team-game-scroll">
            <table className="data-table team-game-table">
              <thead><tr><th>날짜</th><th>결과</th><th>상대</th><th>구분</th><th>스코어</th><th>구장</th><th /></tr></thead>
              <tbody>{data.items.map((game, index) => (
                <tr key={`${game.game_date}-${game.opponent}-${index}`}>
                  <td className={`appearance-date ${game.game_id ? "game-date-cell" : ""}`}>
                    {game.game_id ? <Link className="game-date-link" href={`/teams/${teamCode}/games/${game.game_id}`} rel="noreferrer" target="_blank">{game.game_date}</Link> : game.game_date}
                  </td>
                  <td><span className={`game-result ${game.result === "W" ? "win" : game.result === "L" ? "loss" : "draw"}`}>{resultLabels[game.result]}</span></td>
                  <td><strong>{game.opponent}</strong></td>
                  <td>{game.venue === "home" ? "홈" : "원정"}</td>
                  <td className="score">{game.team_score} : {game.opponent_score}</td>
                  <td>{game.stadium}</td>
                  <td>{game.game_url ? <a aria-label="KBO 경기 리뷰" href={game.game_url} rel="noreferrer" target="_blank"><ArrowUpRight size={15} /></a> : null}</td>
                </tr>
              ))}</tbody>
            </table>
          </DragScroll>
          <a className="appearance-source" href={data.source_url} rel="noreferrer" target="_blank">KBO 공식 일정·결과 <ArrowUpRight size={13} /></a>
        </>
      )}
    </section>
  );
}
