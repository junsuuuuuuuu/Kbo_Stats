"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ErrorPanel, LoadingPanel, SectionTitle } from "@/components/ui";
import { FavoriteButton } from "@/components/favorite-button";
import { api } from "@/lib/api";
import { useFavoritePlayers } from "@/lib/favorites";
import { useDebouncedValue } from "@/lib/use-debounced-value";

export default function PlayersPage() {
  const [input, setInput] = useState("");
  const [page, setPage] = useState(1);
  const { favorites } = useFavoritePlayers();
  const queryText = useDebouncedValue(input.trim(), 300);
  const query = useQuery({
    queryKey: ["players", queryText, page],
    queryFn: ({ signal }) => api.searchPlayers(queryText, undefined, page, signal),
    enabled: queryText.length > 0,
  });
  const totalPages = Math.max(1, Math.ceil((query.data?.total ?? 0) / 30));

  return (
    <div className="page">
      <SectionTitle
        eyebrow="Player Search"
        title="선수를 검색하세요"
        description="동명이인은 생년월일과 역할로 구분됩니다."
      />
      <section className="panel favorites-panel" aria-labelledby="favorite-players-title">
        <div className="panel-header">
          <div>
            <span className="eyebrow">MY PLAYERS</span>
            <h2 id="favorite-players-title">즐겨찾는 선수</h2>
          </div>
          <span className="favorite-count">{favorites.length}명</span>
        </div>
        {favorites.length ? (
          <div className="favorite-player-grid">
            {favorites.map((player) => {
              const role = player.roles.includes("BATTING") ? "batting" : "pitching";
              return (
                <article className="favorite-player-card" key={player.player_id}>
                  <Link href={`/players/${player.player_id}?role=${role}`}>
                    <strong>{player.player_name}</strong>
                    <span>{player.birth_date || "생년월일 정보 없음"}</span>
                    <small>{player.roles.map((item) => item === "BATTING" ? "타자" : "투수").join(" · ")}</small>
                  </Link>
                  <FavoriteButton compact player={player} />
                </article>
              );
            })}
          </div>
        ) : (
          <p className="favorites-empty">선수 상세 페이지에서 별표를 눌러 자주 보는 선수를 모아보세요.</p>
        )}
      </section>
      <form
        className="search-box"
        style={{ marginTop: 20 }}
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
        }}
      >
        <input
          value={input}
          onChange={(event) => { setInput(event.target.value); setPage(1); }}
          placeholder="예: 김도영, 류현진"
          aria-label="선수명"
        />
        <button className="button" type="submit"><Search size={17} />검색</button>
      </form>
      <div className="panel" style={{ marginTop: 20 }}>
        {!queryText ? (
          <div className="state-panel"><Search /><p>분석할 선수 이름을 입력해 주세요.</p></div>
        ) : query.isLoading ? (
          <LoadingPanel />
        ) : query.isError ? (
          <ErrorPanel error={query.error} />
        ) : (
          <>
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr><th>선수</th><th>생년월일</th><th>역할</th><th /></tr></thead>
                <tbody>
                  {query.data?.items.map((player) => {
                    const role = player.roles.includes("BATTING") ? "batting" : "pitching";
                    return (
                      <tr key={player.player_id}>
                        <td><strong>{player.player_name}</strong></td>
                        <td>{player.birth_date}</td>
                        <td>{player.roles.map((item) => <span className="badge" key={item}>{item === "BATTING" ? "타자" : "투수"}</span>)}</td>
                        <td><Link className="button ghost" href={`/players/${player.player_id}?role=${role}`}>분석 보기</Link></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {query.data?.items.length === 0 && <div className="state-panel"><p>검색 결과가 없습니다.</p></div>}
            </div>
            {totalPages > 1 && (
              <div className="panel-header" style={{ marginTop: 18 }}>
                <button className="button ghost" type="button" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>이전</button>
                <span className="muted">{page} / {totalPages} · 총 {query.data?.total ?? 0}명</span>
                <button className="button ghost" type="button" disabled={page === totalPages} onClick={() => setPage((value) => value + 1)}>다음</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
