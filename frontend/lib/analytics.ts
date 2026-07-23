import type { AnalyticsRole } from "@/types/api";
import { LAST_COMPLETE_SEASON } from "./constants";

export type DiscoveryForm = {
  max_age: string;
  min_ops: string;
  min_obp: string;
  min_slg: string;
  min_home_runs: string;
  max_era: string;
  min_strikeouts: string;
};

export function buildDiscoveryParams(role: AnalyticsRole, form: DiscoveryForm) {
  const activeFields = role === "batting"
    ? ["max_age", "min_ops", "min_obp", "min_slg", "min_home_runs"] as const
    : ["max_age", "max_era", "min_strikeouts"] as const;
  const params: Record<string, string | number | undefined> = {
    role,
    season: LAST_COMPLETE_SEASON,
    limit: 50,
  };
  activeFields.forEach((key) => {
    if (form[key]) params[key] = Number(form[key]);
  });
  return params;
}

export function latestCommonSeason(first: number[], second: number[]): number | undefined {
  const secondSeasons = new Set(second);
  return first.filter((season) => secondSeasons.has(season)).sort((a, b) => a - b).at(-1);
}

export function toChartNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}
