"""선수 추천 도메인 서비스의 조건 검색과 유사도 계약 테스트."""

import pandas as pd
import pytest

from app.ml.recommendation import NumericCondition, PlayerRecommendationEngine


def _batting_frame() -> pd.DataFrame:
    common = {
        "season": 2025,
        "team": "KIA",
        "position": "3B",
        "games": 130,
        "plate_appearances": 500,
    }
    rows = [
        {
            **common,
            "player_id": 1,
            "player_name": "기준 선수",
            "age": 24,
            "batting_average": 0.320,
            "on_base_percentage": 0.390,
            "slugging_percentage": 0.550,
            "on_base_plus_slugging": 0.940,
            "home_runs": 28,
            "runs_batted_in": 95,
            "stolen_bases": 25,
            "walks": 55,
            "strikeouts": 80,
        },
        {
            **common,
            "player_id": 2,
            "player_name": "유사 선수",
            "age": 25,
            "batting_average": 0.315,
            "on_base_percentage": 0.385,
            "slugging_percentage": 0.545,
            "on_base_plus_slugging": 0.930,
            "home_runs": 27,
            "runs_batted_in": 93,
            "stolen_bases": 23,
            "walks": 53,
            "strikeouts": 82,
        },
        {
            **common,
            "player_id": 3,
            "player_name": "장타 선수",
            "age": 31,
            "batting_average": 0.250,
            "on_base_percentage": 0.310,
            "slugging_percentage": 0.600,
            "on_base_plus_slugging": 0.910,
            "home_runs": 42,
            "runs_batted_in": 110,
            "stolen_bases": 1,
            "walks": 40,
            "strikeouts": 130,
        },
        {
            **common,
            "player_id": 4,
            "player_name": "표본 부족",
            "age": 22,
            "plate_appearances": 30,
            "batting_average": 0.400,
            "on_base_percentage": 0.450,
            "slugging_percentage": 0.650,
            "on_base_plus_slugging": 1.100,
            "home_runs": 4,
            "runs_batted_in": 10,
            "stolen_bases": 2,
            "walks": 5,
            "strikeouts": 7,
        },
    ]
    return pd.DataFrame(rows)


def test_condition_search_applies_sample_quality_and_ranges() -> None:
    engine = PlayerRecommendationEngine({"batting": _batting_frame()})

    result = engine.search_by_conditions(
        "batting",
        (
            NumericCondition("age", maximum=25),
            NumericCondition("on_base_plus_slugging", minimum=0.9),
        ),
    )

    assert result["player_id"].tolist() == [1, 2]
    assert 4 not in result["player_id"].tolist()


def test_similar_player_combines_algorithms_and_returns_pca() -> None:
    engine = PlayerRecommendationEngine({"batting": _batting_frame()})

    result = engine.recommend_similar("batting", 1, top_k=2)

    assert result.recommendations.iloc[0]["player_id"] == 2
    assert result.recommendations["cosine_score"].between(0, 1).all()
    assert result.recommendations["knn_score"].between(0, 1).all()
    assert len(result.recommendations.iloc[0]["reasons"]) == 3
    assert len(result.pca_coordinates) == 3
    assert result.pca_coordinates["is_reference"].sum() == 1
    assert 0 < sum(result.pca_explained_variance_ratio) <= 1


def test_unknown_filter_column_is_rejected() -> None:
    engine = PlayerRecommendationEngine({"batting": _batting_frame()})

    with pytest.raises(ValueError, match="지원하지 않는 컬럼"):
        engine.search_by_conditions("batting", (NumericCondition("arbitrary_column", minimum=1),))
