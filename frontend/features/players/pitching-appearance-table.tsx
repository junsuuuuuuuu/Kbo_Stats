import { ArrowUpRight, Hand } from "lucide-react";

import { ErrorPanel, LoadingPanel } from "@/components/ui";
import { DragScroll } from "@/components/drag-scroll";
import type { PitchingAppearances } from "@/types/api";

type Props = {
  data?: PitchingAppearances;
  error: Error | null;
  isError: boolean;
  isLoading: boolean;
};

const resultClass = (result: string | null) => {
  if (result === "승") return "win";
  if (result === "패") return "loss";
  return "neutral";
};

export function PitchingAppearanceTable({ data, error, isError, isLoading }: Props) {
  return (
    <section className="section panel appearance-panel">
      <div className="panel-header appearance-heading">
        <div>
          <span className="eyebrow">2026 GAME LOG</span>
          <h2>2026 시즌 등판 기록</h2>
          <p className="muted">날짜별 승·패·세이브·홀드와 투구 내용을 모두 확인하세요.</p>
        </div>
        <div className="appearance-heading-meta">
          <span className="drag-hint"><Hand size={13} /> 드래그해서 보기</span>
          {data ? <strong className="appearance-count">총 {data.items.length}경기</strong> : null}
        </div>
      </div>

      {isLoading ? <LoadingPanel label="등판 기록을 불러오고 있습니다" /> : null}
      {isError ? <ErrorPanel error={error} /> : null}
      {!isLoading && !isError && data?.items.length === 0 ? (
        <div className="state-panel"><p>2026 시즌 등판 기록이 없습니다.</p></div>
      ) : null}
      {data?.items.length ? (
        <DragScroll className="table-wrap appearance-table-wrap">
          <table className="data-table appearance-table">
            <thead>
              <tr>
                <th>날짜</th><th>상대</th><th>구분</th><th>결과</th><th>이닝</th>
                <th>타자</th><th>피안타</th><th>홈런</th><th>볼넷</th><th>사구</th>
                <th>삼진</th><th>실점</th><th>자책</th><th>경기 ERA</th><th>시즌 ERA</th>
              </tr>
            </thead>
            <tbody>
              {[...data.items].reverse().map((item) => (
                <tr key={`${item.game_date}-${item.opponent}`}>
                  <td className="appearance-date">{item.game_date.slice(5).replace("-", ".")}</td>
                  <td><b>{item.opponent}</b></td>
                  <td>{item.appearance_type}</td>
                  <td><span className={`game-result ${resultClass(item.result)}`}>{item.result ?? "-"}</span></td>
                  <td className="score">{item.innings_pitched}</td>
                  <td>{item.batters_faced}</td><td>{item.hits_allowed}</td><td>{item.home_runs_allowed}</td>
                  <td>{item.walks_allowed}</td><td>{item.hit_batters}</td><td>{item.strikeouts}</td>
                  <td>{item.runs_allowed}</td><td className="earned-runs">{item.earned_runs}</td>
                  <td>{item.game_era.toFixed(2)}</td><td>{item.season_era.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </DragScroll>
      ) : null}
      {data ? (
        <a className="appearance-source" href={data.source_url} target="_blank" rel="noreferrer">
          KBO 공식 일자별 기록 <ArrowUpRight size={14} />
        </a>
      ) : null}
    </section>
  );
}
