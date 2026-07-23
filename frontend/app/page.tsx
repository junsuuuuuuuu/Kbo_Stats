import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { CurrentValueRanking } from "@/features/rankings/current-value-ranking";
import { LatestGameDayTable } from "@/features/teams/latest-game-day";

export default function HomePage() {
  return (
    <div className="page">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">KBO DATA &amp; AI · 1982—2026</span>
          <h1>쌓인 기록에서,<br /><em>다음 가능성을 봅니다.</em></h1>
          <p>
            1982년부터 오늘까지의 KBO 기록을 한곳에서 살펴보세요.
            선수 비교부터 현재 가치, 성장 흐름과 다음 시즌까지 데이터로 더 깊이 읽어드립니다.
          </p>
          <div className="hero-actions">
            <Link className="button" href="/players">선수 기록 탐색하기<ArrowRight size={17} /></Link>
            <Link className="button secondary" href="/discover">AI 분석 둘러보기<ArrowRight size={16} /></Link>
          </div>
        </div>
        <aside className="hero-stats" aria-label="서비스 데이터 범위">
          <div className="hero-stat"><strong>45</strong><span>시즌의 기록</span></div>
          <div className="hero-stat"><strong>5</strong><span>AI 분석 기능</span></div>
          <div className="hero-stat"><strong>10</strong><span>KBO 구단</span></div>
        </aside>
      </section>
      <LatestGameDayTable />
      <section className="section"><CurrentValueRanking /></section>
    </div>
  );
}
