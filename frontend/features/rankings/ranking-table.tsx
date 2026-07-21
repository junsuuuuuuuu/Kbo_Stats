"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { ErrorPanel, LoadingPanel, ScoreBar } from "@/components/ui";
import { api } from "@/lib/api";
import type { AnalyticsRole } from "@/types/api";

interface RankingTableProps {
  role: AnalyticsRole;
  season?: number;
  limit?: number;
}

export function RankingTable({ role, season = 2025, limit = 20 }: RankingTableProps) {
  const query = useQuery({
    queryKey: ["rankings", role, season, limit],
    queryFn: () => api.rankings(role, season, undefined, limit),
  });

  if (query.isLoading) {
    return <LoadingPanel label={`${season} 가치 점수를 계산하고 있습니다`} />;
  }
  if (query.isError) return <ErrorPanel error={query.error} />;

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>순위</th>
            <th>선수</th>
            <th>{season} 소속</th>
            <th>AI Score</th>
            <th>강점</th>
          </tr>
        </thead>
        <tbody>
          {query.data?.items.map((item) => (
            <tr key={item.player_id}>
              <td className="rank">#{item.season_rank}</td>
              <td>
                <Link href={`/players/${item.player_id}?role=${role}`}>
                  <strong>{item.player_name}</strong>
                </Link>
              </td>
              <td>{item.team}</td>
              <td className="score">{item.ai_score.toFixed(1)}</td>
              <td style={{ minWidth: 190 }}>
                <ScoreBar
                  label={item.reasons[0] ?? "종합 가치"}
                  value={item.ai_score}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
