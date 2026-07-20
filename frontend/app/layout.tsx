import type { Metadata } from "next";

import { Header } from "@/components/header";
import { Providers } from "@/app/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "KBO AI Player Analytics",
  description: "1982~2025 KBO 기록 기반 AI 선수 분석 플랫폼",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko" suppressHydrationWarning><body><Providers><Header /><main>{children}</main></Providers></body></html>;
}
