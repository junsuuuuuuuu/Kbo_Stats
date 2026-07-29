import { ArrowRight, BarChart3, Database, Sparkles } from "lucide-react";
import Link from "next/link";

import { CurrentValueRanking } from "@/features/rankings/current-value-ranking";
import { LatestGameDayTable } from "@/features/teams/latest-game-day";
import { PROJECT_METRICS } from "@/lib/project-metrics";

const scaleCards = [
  { value: `${PROJECT_METRICS.seasons}년+`, label: "KBO 시즌 데이터", icon: Database },
  { value: PROJECT_METRICS.players.toLocaleString("ko-KR"), label: "선수 프로필", icon: BarChart3 },
  { value: PROJECT_METRICS.seasonRecords.toLocaleString("ko-KR"), label: "시즌별 선수 기록", icon: BarChart3 },
  { value: `${PROJECT_METRICS.aiAnalyses}가지`, label: "AI 분석 기능", icon: Sparkles },
];

export default function HomePage() {
  return (
    <div className="page">
      <section className="hero landing-hero">
        <div className="hero-copy landing-hero-copy">
          <span className="eyebrow">KBO DATA &amp; AI <i>•</i> 1982–2026</span>
          <h1>1982~2026 KBO 선수 데이터를<br /><em>분석.</em></h1>
          <p>45년의 선수 기록을 모아 비교·예측·추천까지 연결하는 KBO 데이터 분석 플랫폼입니다.</p>
          <div className="hero-actions">
            <Link className="button" href="/players">선수 탐색하기 <ArrowRight size={17} /></Link>
            <Link className="button secondary" href="/discover">AI 분석 보기 <ArrowRight size={16} /></Link>
          </div>
          <div className="hero-proof"><span><i />1982–2026 데이터 범위</span><span><i />2026 시즌 진행 데이터 포함</span></div>
        </div>
        <aside className="hero-scale-card" aria-label="프로젝트 데이터 규모">
          <div className="hero-scale-header">{PROJECT_METRICS.asOf}</div>
          <div className="hero-scale-list">
            {scaleCards.map(({ value, label, icon: Icon }) => <div className="hero-scale-item" key={label}><span className="hero-scale-icon"><Icon size={16} /></span><div><strong>{value}</strong><span>{label}</span></div></div>)}
          </div>
          <div className="hero-scale-footer"><span>기록 수집</span><i /><span>지표 정규화</span><i /><span>AI 인사이트</span></div>
        </aside>
      </section>
      <LatestGameDayTable />
      <section className="section"><CurrentValueRanking /></section>
      <footer className="data-source-note">
        <p>본 서비스는 KBO 공식 공개 기록을 기반으로 선수와 팀 데이터를 탐색·비교·분석하는 프로젝트입니다. 데이터는 수집 시점에 따라 실제 공식 기록과 차이가 있을 수 있습니다.</p>
        <a href="https://www.koreabaseball.com" rel="noreferrer" target="_blank">출처: KBO 공식 홈페이지</a>
      </footer>
    </div>
  );
}
