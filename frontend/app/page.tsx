import { ArrowRight, BrainCircuit, ChartNoAxesCombined, GitCompareArrows, Search, Sparkles, Target, Trophy } from "lucide-react";
import Link from "next/link";

import { RankingTable } from "@/features/rankings/ranking-table";
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
  return <div className="page"><section className="hero"><div className="hero-grid" /><span className="eyebrow">1982—2025 KBO DATA INTELLIGENCE</span><h1>숫자 너머의<br /><em>선수 가치</em>를 읽다.</h1><p>43년 KBO 시즌 기록을 머신러닝과 설명 가능한 분석으로 연결한 선수 인텔리전스 플랫폼입니다.</p><div className="hero-actions"><Link className="button" href="/players"><Search size={18} />선수 분석<ArrowRight size={17} /></Link><Link className="button secondary" href="/rankings"><Trophy size={18} />선수 가치 랭킹</Link></div></section><section className="section"><SectionTitle eyebrow="Analytics Suite" title="하나의 기록, 여섯 가지 관점" description="모든 분석은 자체 학습 모델과 재현 가능한 통계 규칙으로 계산됩니다." /><div className="feature-grid">{features.map(({ icon: Icon, title, text }) => <article className="feature-card" key={title}><span className="feature-icon"><Icon size={21} /></span><h3>{title}</h3><p>{text}</p></article>)}</div></section><section className="section"><div className="panel"><div className="panel-header"><div><span className="eyebrow">2025 AI RANKING</span><h2>타자 가치 TOP 5</h2></div><Link className="button ghost" href="/rankings">전체 보기<ArrowRight size={16} /></Link></div><RankingTable role="batting" limit={5} /></div></section></div>;
}
