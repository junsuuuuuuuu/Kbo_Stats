import type { Metadata } from "next";

import { Header } from "@/components/header";
import { Providers } from "@/app/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "KBO Records — 선수 기록과 커리어 분석",
  description: "1982~2025 KBO 기록을 탐색하고 선수의 커리어를 비교하는 데이터 플랫폼",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko" suppressHydrationWarning><body><Providers><Header /><main>{children}</main></Providers></body></html>;
}
