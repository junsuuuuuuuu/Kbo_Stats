"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useState } from "react";

import { api } from "@/lib/api";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import type { PlayerSummary } from "@/types/api";

export function PlayerPicker({ label, selected, onSelect }: { label: string; selected: PlayerSummary | null; onSelect: (player: PlayerSummary) => void }) {
  const [queryText, setQueryText] = useState("");
  const debouncedQuery = useDebouncedValue(queryText.trim(), 300);
  const query = useQuery({ queryKey: ["picker", debouncedQuery], queryFn: ({ signal }) => api.searchPlayers(debouncedQuery, undefined, 1, signal), enabled: debouncedQuery.length >= 1 });
  return <div className="panel"><div className="field"><label>{label}</label><div className="search-box"><input value={queryText} onChange={(event) => setQueryText(event.target.value)} placeholder={selected ? "다른 선수 검색" : "선수명 검색"} /><Search size={18} /></div></div>{selected && <h3 style={{ marginBottom: 0 }}>{selected.player_name} <span className="badge">{selected.roles.join(" · ")}</span></h3>}{queryText && <div style={{ marginTop: 10 }}>{query.data?.items.slice(0, 6).map((player) => <button key={player.player_id} type="button" onClick={() => { onSelect(player); setQueryText(""); }} style={{ width: "100%", textAlign: "left", border: 0, borderBottom: "1px solid var(--line)", background: "transparent", color: "var(--text)", padding: 10, cursor: "pointer" }}>{player.player_name} <small className="muted">{player.birth_date}</small></button>)}</div>}</div>;
}
