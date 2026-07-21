import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { CurrentValueRanking } from "@/features/rankings/current-value-ranking";
import { LatestGameDayTable } from "@/features/teams/latest-game-day";

export default function HomePage() {
  return <div className="page"><section className="hero"><div className="hero-copy"><span className="eyebrow">KBO RECORD ARCHIVE · 1982—2026</span><h1>기록을 읽으면,<br /><em>선수가 보입니다.</em></h1><p>현재 시즌을 포함한 KBO 기록을 한곳에서 탐색하고, 선수의 다음 시즌과 커리어 흐름을 더 깊이 이해하세요.</p><div className="hero-actions"><Link className="button" href="/players">선수 찾아보기<ArrowRight size={17} /></Link><Link className="button secondary" href="/rankings">가치 랭킹 보기<ArrowRight size={16} /></Link></div></div><aside className="hero-stats" aria-label="데이터 범위"><div className="hero-stat"><strong>45</strong><span>시즌 데이터</span></div><div className="hero-stat"><strong>6</strong><span>분석 관점</span></div><div className="hero-stat"><strong>10</strong><span>KBO 구단</span></div></aside></section><LatestGameDayTable /><section className="section"><CurrentValueRanking /></section></div>;
}
