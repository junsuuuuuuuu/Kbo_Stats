"""AI 가치 점수의 순위, 역할 방향, 팀 순위 테스트."""

import pandas as pd

from app.ml.ranking import PlayerValueRanker
from app.ml.ranking_config import RANKING_SPECS


def _batting_frame() -> pd.DataFrame:
    rows = []
    for season in (2024, 2025):
        for player_id, ops in ((1, 1.0), (2, 0.8), (3, 0.6)):
            rows.append(
                {
                    "player_id": player_id,
                    "player_name": f"선수 {player_id}",
                    "season": season,
                    "team": "KIA" if player_id < 3 else "LG",
                    "age": 22 + player_id,
                    "games": 140 - player_id,
                    "plate_appearances": 500,
                    "runs": 100 - player_id * 10,
                    "home_runs": 35 - player_id * 10,
                    "runs_batted_in": 100 - player_id * 10,
                    "stolen_bases": 20 - player_id * 5,
                    "walks": 70 - player_id * 10,
                    "batting_average": ops / 3,
                    "on_base_percentage": ops * 0.42,
                    "slugging_percentage": ops * 0.58,
                    "on_base_plus_slugging": ops,
                }
            )
    return pd.DataFrame(rows)


def test_best_all_around_batter_ranks_first() -> None:
    result = PlayerValueRanker({"batting": _batting_frame()}).rank_season("batting", season=2025)

    assert result.iloc[0]["player_id"] == 1
    assert result.iloc[0]["season_rank"] == 1
    assert result["ai_score"].between(0, 100).all()
    assert len(result.iloc[0]["reasons"]) == 3


def test_team_filter_preserves_league_and_team_rank() -> None:
    result = PlayerValueRanker({"batting": _batting_frame()}).rank_season(
        "batting", season=2025, team="KIA"
    )

    assert result["season_rank"].tolist() == [1, 2]
    assert result["team_rank"].tolist() == [1, 2]


def test_batting_value_types_recalculate_score_and_expose_defense_component() -> None:
    frame = _batting_frame()
    frame["errors"] = [0, 4, 8, 0, 4, 8]
    ranker = PlayerValueRanker({"batting": frame})

    offense = ranker.rank_season("batting", season=2025, value_type="offense")
    defense = ranker.rank_season("batting", season=2025, value_type="defense")

    assert "defense_score" in defense.columns
    assert offense["ai_score"].tolist() != defense["ai_score"].tolist()
    assert defense.iloc[0]["player_id"] == 1


def test_consistency_does_not_join_non_consecutive_seasons() -> None:
    def row(player_id: int, season: int, ops: float) -> dict[str, float | int]:
        return {
            "player_id": player_id,
            "season": season,
            "plate_appearances": 500,
            "on_base_plus_slugging": ops,
        }

    frame = pd.DataFrame(
        [
            row(1, 2020, 0.8),
            row(1, 2022, 0.8),
            row(1, 2025, 0.8),
            row(2, 2024, 0.7),
            row(2, 2025, 0.9),
        ]
    )
    season_frame = frame.loc[frame["season"].eq(2025)].copy()

    scores = PlayerValueRanker()._consistency(
        frame, season_frame, RANKING_SPECS["batting"]
    )

    assert scores.iloc[0] == 0.5
    assert scores.iloc[1] == 1.0
