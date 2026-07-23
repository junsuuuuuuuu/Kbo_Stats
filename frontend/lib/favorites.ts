"use client";

import { useSyncExternalStore } from "react";

import type { PlayerRole, PlayerSummary } from "@/types/api";

const STORAGE_KEY = "next-record:favorites:v1";
const CHANGE_EVENT = "next-record:favorites-changed";
const EMPTY_FAVORITES: PlayerSummary[] = [];

let cachedRaw: string | null = null;
let cachedFavorites = EMPTY_FAVORITES;

function isPlayerRole(value: unknown): value is PlayerRole {
  return value === "BATTING" || value === "PITCHING";
}

function isPlayerSummary(value: unknown): value is PlayerSummary {
  if (!value || typeof value !== "object") return false;
  const player = value as Partial<PlayerSummary>;
  return (
    typeof player.player_id === "number"
    && typeof player.player_name === "string"
    && typeof player.birth_date === "string"
    && Array.isArray(player.roles)
    && player.roles.every(isPlayerRole)
  );
}

export function parseFavorites(value: string | null): PlayerSummary[] {
  if (!value) return EMPTY_FAVORITES;
  try {
    const parsed: unknown = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.filter(isPlayerSummary) : EMPTY_FAVORITES;
  } catch {
    return EMPTY_FAVORITES;
  }
}

function getFavoritesSnapshot() {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return EMPTY_FAVORITES;
  }
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cachedFavorites = parseFavorites(raw);
  }
  return cachedFavorites;
}

function subscribe(onStoreChange: () => void) {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(CHANGE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(CHANGE_EVENT, onStoreChange);
  };
}

function saveFavorites(favorites: PlayerSummary[]) {
  const raw = JSON.stringify(favorites);
  try {
    window.localStorage.setItem(STORAGE_KEY, raw);
  } catch {
    return;
  }
  cachedRaw = raw;
  cachedFavorites = favorites;
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function useFavoritePlayers() {
  const favorites = useSyncExternalStore(subscribe, getFavoritesSnapshot, () => EMPTY_FAVORITES);

  return {
    favorites,
    isFavorite: (playerId: number) => favorites.some((player) => player.player_id === playerId),
    toggleFavorite: (player: PlayerSummary) => {
      const current = getFavoritesSnapshot();
      const exists = current.some((item) => item.player_id === player.player_id);
      saveFavorites(exists
        ? current.filter((item) => item.player_id !== player.player_id)
        : [player, ...current]);
    },
  };
}
