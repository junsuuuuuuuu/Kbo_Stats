"use client";

import { Star } from "lucide-react";

import { useFavoritePlayers } from "@/lib/favorites";
import type { PlayerSummary } from "@/types/api";

export function FavoriteButton({
  compact = false,
  player,
}: {
  compact?: boolean;
  player: PlayerSummary;
}) {
  const { isFavorite, toggleFavorite } = useFavoritePlayers();
  const active = isFavorite(player.player_id);
  const label = active ? "즐겨찾기 해제" : "즐겨찾기 추가";

  return (
    <button
      aria-label={`${player.player_name} ${label}`}
      aria-pressed={active}
      className={`favorite-button${active ? " active" : ""}${compact ? " compact" : ""}`}
      onClick={() => toggleFavorite(player)}
      title={label}
      type="button"
    >
      <Star aria-hidden="true" fill={active ? "currentColor" : "none"} size={18} />
      {!compact && <span>{active ? "즐겨찾는 선수" : "즐겨찾기"}</span>}
    </button>
  );
}
