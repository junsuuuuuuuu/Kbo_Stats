import { ArrowUpRight, Hand } from "lucide-react";

import { DragScroll } from "@/components/drag-scroll";
import { ErrorPanel, LoadingPanel } from "@/components/ui";
import type { BattingAppearances } from "@/types/api";

type Props = {
  data?: BattingAppearances;
  error: Error | null;
  isError: boolean;
  isLoading: boolean;
};

const average = (value: number | null) => value == null ? "-" : value.toFixed(3);

export function BattingAppearanceTable({ data, error, isError, isLoading }: Props) {
  return (
    <section className="section panel appearance-panel">
      <div className="panel-header appearance-heading">
        <div>
          <span className="eyebrow">2026 GAME LOG</span>
          <h2>2026 시즌 경기 기록</h2>
          <p className="muted">교체 출장을 포함한 날짜별 타격 기록입니다.</p>
        </div>
        <div className="appearance-heading-meta">
          <span className="drag-hint"><Hand size={13} /> 드래그해서 보기</span>
          {data ? <strong className="appearance-count">총 {data.items.length}경기</strong> : null}
        </div>
      </div>

      {isLoading ? <LoadingPanel label="경기 기록을 불러오고 있습니다" /> : null}
      {isError ? <ErrorPanel error={error} /> : null}
      {!isLoading && !isError && data?.items.length === 0 ? (
        <div className="state-panel"><p>2026 시즌 경기 기록이 없습니다.</p></div>
      ) : null}
      {data?.items.length ? (
        <DragScroll className="table-wrap appearance-table-wrap">
          <table className="data-table appearance-table batting-game-table">
            <thead>
              <tr>
                <th>날짜</th><th>상대</th><th>타수</th><th>타석</th><th>안타</th>
                <th>2루타</th><th>3루타</th><th>홈런</th><th>득점</th><th>타점</th>
                <th>도루</th><th>도실</th><th>볼넷</th><th>사구</th><th>삼진</th>
                <th>병살</th><th>경기 AVG</th><th>시즌 AVG</th>
              </tr>
            </thead>
            <tbody>
              {[...data.items].reverse().map((item) => (
                <tr key={`${item.game_date}-${item.opponent}`}>
                  <td className="appearance-date">{item.game_date.slice(5).replace("-", ".")}</td>
                  <td><b>{item.opponent}</b></td><td>{item.at_bats}</td><td>{item.plate_appearances}</td>
                  <td className="primary-stat">{item.hits}</td><td>{item.doubles}</td><td>{item.triples}</td>
                  <td className={item.home_runs ? "home-run" : ""}>{item.home_runs}</td>
                  <td>{item.runs}</td><td>{item.runs_batted_in}</td><td>{item.stolen_bases}</td>
                  <td>{item.caught_stealing}</td><td>{item.walks}</td><td>{item.hit_by_pitch}</td>
                  <td>{item.strikeouts}</td><td>{item.grounded_into_double_play}</td>
                  <td>{average(item.game_average)}</td><td>{average(item.season_average)}</td>
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
