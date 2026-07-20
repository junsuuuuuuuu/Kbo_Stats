"use client";

import { AlertCircle } from "lucide-react";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="page">
      <div className="state-panel error">
        <AlertCircle />
        <p>페이지를 불러오는 중 오류가 발생했습니다.</p>
        <button className="button" type="button" onClick={reset}>다시 시도</button>
      </div>
    </div>
  );
}
