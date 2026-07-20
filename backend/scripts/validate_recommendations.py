"""실제 정제 데이터로 조건 검색과 유사 선수 추천 결과를 검증한다."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.ml.artifacts import file_sha256, write_json
from app.ml.recommendation import NumericCondition, PlayerRecommendationEngine
from app.ml.recommendation_config import RECOMMENDATION_SPECS

REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "ml"
    / "reports"
    / ("recommendation_validation.json")
)


def _example_payload(role: str, player_id: int, engine: PlayerRecommendationEngine) -> dict:
    result = engine.recommend_similar(role, player_id, season=2025, top_k=10)
    return {
        "reference_player_id": player_id,
        "recommendation_count": len(result.recommendations),
        "recommended_player_ids": result.recommendations["player_id"].astype(int).tolist(),
        "similarity_score_range": {
            "minimum": float(result.recommendations["similarity_score"].min()),
            "maximum": float(result.recommendations["similarity_score"].max()),
        },
        "pca_point_count": len(result.pca_coordinates),
        "pca_explained_variance_ratio": list(result.pca_explained_variance_ratio),
    }


def main() -> None:
    """두 역할의 검색·추천 smoke test 결과와 원본 checksum을 저장한다."""

    engine = PlayerRecommendationEngine()
    batting_pool = engine.search_by_conditions("batting", season=2025, limit=10_000)
    pitching_pool = engine.search_by_conditions("pitching", season=2025, limit=10_000)
    young_sluggers = engine.search_by_conditions(
        "batting",
        (
            NumericCondition("age", maximum=25),
            NumericCondition("on_base_plus_slugging", minimum=0.8),
        ),
        season=2025,
        limit=10_000,
    )
    effective_pitchers = engine.search_by_conditions(
        "pitching",
        (
            NumericCondition("earned_run_average", maximum=4.0),
            NumericCondition("strikeouts", minimum=50),
        ),
        season=2025,
        limit=10_000,
    )
    if young_sluggers.empty or effective_pitchers.empty:
        raise RuntimeError("실제 데이터 추천 검증에 필요한 예시 조건 결과가 없습니다.")

    report = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "season": 2025,
        "algorithm": "standard scaling + cosine similarity + KNN + PCA",
        "sources": {
            role: {
                "path": spec.source_path.name,
                "sha256": file_sha256(spec.source_path),
            }
            for role, spec in RECOMMENDATION_SPECS.items()
        },
        "eligible_candidate_counts": {
            "batting": len(batting_pool),
            "pitching": len(pitching_pool),
        },
        "condition_examples": {
            "age_lte_25_and_ops_gte_0_8": len(young_sluggers),
            "era_lte_4_and_strikeouts_gte_50": len(effective_pitchers),
        },
        "similarity_examples": {
            "batting": _example_payload(
                "batting", int(young_sluggers.iloc[0]["player_id"]), engine
            ),
            "pitching": _example_payload(
                "pitching", int(effective_pitchers.iloc[0]["player_id"]), engine
            ),
        },
    }
    write_json(REPORT_PATH, report)
    print(f"추천 검증 보고서 저장 완료: {REPORT_PATH}")


if __name__ == "__main__":
    main()
