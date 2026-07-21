const rateMetrics = new Set([
  "batting_average",
  "on_base_percentage",
  "slugging_percentage",
  "on_base_plus_slugging",
  "defensive_efficiency",
  "isolated_power",
  "batting_average_on_balls_in_play",
  "weighted_on_base_average",
  "earned_run_average",
  "peak_ops",
  "peak_era",
]);

export function formatMetric(key: string, value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (rateMetrics.has(key)) return value.toFixed(3);
  if (["walk_percentage", "strikeout_percentage", "stolen_base_percentage"].includes(key)) return `${(value * 100).toFixed(1)}%`;
  if (key === "weighted_runs_created_plus") return `${value.toFixed(0)}`;
  if (key === "peak_age") return `${value.toFixed(1)}세`;
  return value.toFixed(1);
}

export function normalizePair(
  first: number,
  second: number,
  lowerIsBetter = false,
): [number, number] {
  let adjustedFirst = Math.max(first, 0);
  let adjustedSecond = Math.max(second, 0);
  if (lowerIsBetter) {
    const ceiling = Math.max(adjustedFirst, adjustedSecond, 1);
    adjustedFirst = ceiling - adjustedFirst;
    adjustedSecond = ceiling - adjustedSecond;
  }
  const maximum = Math.max(adjustedFirst, adjustedSecond, 0.0001);
  return [(adjustedFirst / maximum) * 100, (adjustedSecond / maximum) * 100];
}
