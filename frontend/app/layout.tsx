import type { Metadata } from "next";

import { Header } from "@/components/header";
import { Providers } from "@/app/providers";

import "./globals.css";
import { CURRENT_SEASON, FIRST_KBO_SEASON } from "@/lib/constants";

export const metadata: Metadata = {
  title: "기록의 다음 — KBO 데이터 & AI",
  description: `${FIRST_KBO_SEASON}~${CURRENT_SEASON} KBO 기록과 현재 가치, 성장 흐름, 다음 시즌을 함께 살펴보는 야구 데이터 분석 서비스`,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko" suppressHydrationWarning><body><Providers><Header /><main>{children}</main></Providers></body></html>;
}
