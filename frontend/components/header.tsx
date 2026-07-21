import { Activity, GitCompareArrows, Search, Sparkles, Trophy, UsersRound } from "lucide-react";
import Link from "next/link";

import { ThemeToggle } from "@/components/theme-toggle";

const links = [
  { href: "/players", label: "선수 검색", icon: Search },
  { href: "/teams", label: "구단 로스터", icon: UsersRound },
  { href: "/discover", label: "AI 스카우팅", icon: Sparkles },
  { href: "/rankings", label: "가치 랭킹", icon: Trophy },
  { href: "/compare", label: "선수 비교", icon: GitCompareArrows },
];

export function Header() {
  return (
    <header className="site-header">
      <Link href="/" className="brand">
        <span className="brand-mark"><Activity size={20} /></span>
        <span>KBO <strong>분석</strong></span>
      </Link>
      <nav className="nav-links">
        {links.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href}><Icon size={16} />{label}</Link>
        ))}
      </nav>
      <ThemeToggle />
    </header>
  );
}
