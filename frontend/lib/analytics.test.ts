import { describe, expect, it } from "vitest";

import { buildDiscoveryParams, latestCommonSeason, toChartNumber } from "./analytics";

const form = {
  max_age: "25",
  min_ops: "0.8",
  min_obp: "",
  min_slg: "",
  min_home_runs: "",
  max_era: "4.0",
  min_strikeouts: "50",
};

describe("buildDiscoveryParams", () => {
  it("타자 검색에서 투수 필터를 제외한다", () => {
    expect(buildDiscoveryParams("batting", form)).toEqual({
      role: "batting", season: 2025, limit: 50, max_age: 25, min_ops: 0.8,
    });
  });

  it("투수 검색에서 타자 필터를 제외한다", () => {
    expect(buildDiscoveryParams("pitching", form)).toEqual({
      role: "pitching", season: 2025, limit: 50, max_age: 25, max_era: 4, min_strikeouts: 50,
    });
  });
});

describe("chart helpers", () => {
  it("두 선수의 공통 최신 시즌을 찾는다", () => {
    expect(latestCommonSeason([2021, 2023, 2025], [2022, 2023, 2024])).toBe(2023);
  });

  it("결측치를 0으로 바꾸지 않는다", () => {
    expect(toChartNumber(null)).toBeNull();
    expect(toChartNumber(undefined)).toBeNull();
    expect(toChartNumber("not-a-number")).toBeNull();
    expect(toChartNumber("0.812")).toBe(0.812);
  });
});
