import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ErrorPanel, MetricCard, ScoreBar, SectionTitle } from "./ui";

describe("shared UI components", () => {
  it("renders optional section copy only when supplied", () => {
    const html = renderToStaticMarkup(
      <SectionTitle eyebrow="Player Search" title="선수 검색" description="이름으로 찾기" />,
    );

    expect(html).toContain("Player Search");
    expect(html).toContain("이름으로 찾기");
  });

  it("exposes metric help text to keyboard and screen-reader users", () => {
    const html = renderToStaticMarkup(
      <MetricCard label="OPS" value="0.923" description="출루율과 장타율의 합" />,
    );

    expect(html).toContain('aria-label="OPS: 출루율과 장타율의 합"');
    expect(html).toContain('tabindex="0"');
  });

  it("clamps score bars and renders safe error copy", () => {
    expect(renderToStaticMarkup(<ScoreBar label="ai_score" value={120} />)).toContain(
      "width:100%",
    );
    expect(renderToStaticMarkup(<ErrorPanel error="bad response" />)).toContain(
      "오류가 발생했습니다.",
    );
  });
});
