import { describe, expect, it } from "vitest";

import { parseFavorites } from "./favorites";

describe("favorite player storage", () => {
  it("restores valid saved players", () => {
    const favorite = {
      player_id: 7,
      player_name: "테스트 선수",
      birth_date: "2000-01-01",
      roles: ["BATTING"],
    };

    expect(parseFavorites(JSON.stringify([favorite]))).toEqual([favorite]);
  });

  it("ignores malformed storage values and entries", () => {
    expect(parseFavorites("not-json")).toEqual([]);
    expect(parseFavorites(JSON.stringify([{ player_id: "7" }, null]))).toEqual([]);
  });
});
