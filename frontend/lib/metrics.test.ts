import { describe, expect, it } from "vitest";

import { formatMetric, normalizePair } from "./metrics";

describe("formatMetric", () => {
  it("비율 기록과 나이를 사용자 표시 형식으로 변환한다", () => {
    expect(formatMetric("on_base_plus_slugging", 0.9234)).toBe("0.923");
    expect(formatMetric("peak_age", 27.26)).toBe("27.3세");
    expect(formatMetric("home_runs", null)).toBe("—");
  });
});

describe("normalizePair", () => {
  it("큰 값과 낮을수록 좋은 값의 방향을 보존한다", () => {
    expect(normalizePair(20, 10)).toEqual([100, 50]);
    const [firstEra, secondEra] = normalizePair(2, 4, true);
    expect(firstEra).toBeGreaterThan(secondEra);
  });
});
