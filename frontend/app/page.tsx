import { ArrowRight, BrainCircuit, ChartNoAxesCombined, GitCompareArrows, Sparkles, Target, Trophy } from "lucide-react";
import Link from "next/link";

import { CurrentValueRanking } from "@/features/rankings/current-value-ranking";
import { SectionTitle } from "@/components/ui";

const features = [
  { icon: BrainCircuit, title: "다음 시즌 예측", text: "최근 3년 기록과 검증된 앙상블 모델로 AVG, OPS, HR, ERA, SO를 예측합니다." },
  { icon: Sparkles, title: "유사 선수 추천", text: "Cosine·KNN 유사도와 PCA로 플레이 스타일이 가까운 선수를 설명합니다." },
  { icon: ChartNoAxesCombined, title: "성장곡선", text: "리그 변화 분포를 기준으로 급성장과 하락 시즌을 자동 탐지합니다." },
  { icon: Target, title: "전성기 예측", text: "초기 커리어에서 Peak Age와 커리어 최고 기록을 예측합니다." },
  { icon: Trophy, title: "AI 가치 랭킹", text: "공격·꾸준함·출장·팀 기여를 결합한 설명 가능한 0~100 점수입니다." },
  { icon: GitCompareArrows, title: "선수 비교", text: "두 선수의 시즌 기록과 강점을 Radar·Bar·Line chart로 비교합니다." },
];

export default function HomePage() {
  return <div className="page"><section className="hero"><div className="hero-copy"><span className="eyebrow">KBO RECORD ARCHIVE · 1982—2026</span><h1>기록을 읽으면,<br /><em>선수가 보입니다.</em></h1><p>현재 시즌을 포함한 KBO 기록을 한곳에서 탐색하고, 선수의 다음 시즌과 커리어 흐름을 더 깊이 이해하세요.</p><div className="hero-actions"><Link className="button" href="/players">선수 찾아보기<ArrowRight size={17} /></Link><Link className="button secondary" href="/rankings">가치 랭킹 보기<ArrowRight size={16} /></Link></div></div><aside className="hero-stats" aria-label="데이터 범위"><div className="hero-stat"><strong>45</strong><span>시즌 데이터</span></div><div className="hero-stat"><strong>6</strong><span>분석 관점</span></div><div className="hero-stat"><strong>10</strong><span>KBO 구단</span></div></aside></section><section className="section"><SectionTitle eyebrow="Explore the data" title="선수를 이해하는 여섯 가지 방법" description="복잡한 모델 설명보다, 실제 기록에서 발견할 수 있는 변화와 비교에 집중했습니다." /><div className="feature-grid">{features.map(({ icon: Icon, title, text }) => <article className="feature-card" key={title}><span className="feature-icon"><Icon size={21} strokeWidth={1.7} /></span><h3>{title}</h3><p>{text}</p></article>)}</div></section><section className="section"><CurrentValueRanking /></section></div>;
}
