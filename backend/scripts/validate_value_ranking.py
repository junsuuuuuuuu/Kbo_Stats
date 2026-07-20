"""2025 시즌 AI 가치 랭킹의 실제 데이터 검증 보고서 생성."""

from datetime import UTC, datetime
from pathlib import Path

from app.ml.artifacts import file_sha256, write_json
from app.ml.ranking import PlayerValueRanker
from app.ml.ranking_config import RANKING_SPECS

REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "ml"
    / "reports"
    / ("value_ranking_validation.json")
)


def main() -> None:
    ranker = PlayerValueRanker()
    roles = {}
    for role, spec in RANKING_SPECS.items():
        ranking = ranker.rank_season(role, season=2025, limit=10_000)
        roles[role] = {
            "eligible_player_count": len(ranking),
            "team_count": int(ranking["team"].nunique()),
            "score_min": float(ranking["ai_score"].min()),
            "score_mean": float(ranking["ai_score"].mean()),
            "score_max": float(ranking["ai_score"].max()),
            "top_10_player_ids": ranking.head(10)["player_id"].astype(int).tolist(),
            "component_weights": spec.component_weights,
            "source_sha256": file_sha256(spec.source_path),
        }
    write_json(
        REPORT_PATH,
        {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "season": 2025,
            "score_range": [0, 100],
            "roles": roles,
        },
    )
    print(f"가치 랭킹 검증 보고서 저장 완료: {REPORT_PATH}")


if __name__ == "__main__":
    main()
