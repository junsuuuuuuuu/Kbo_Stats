"""성장곡선의 연속 시즌, 표본 기준, 지표 방향 판정 테스트."""

import pandas as pd
import pytest

from app.ml.growth import PlayerGrowthAnalyzer


def _batting_population() -> pd.DataFrame:
    changes = [-0.20, -0.10, 0.0, 0.10, 0.20]
    rows = []
    for player_id, change in enumerate(changes, start=1):
        for season, ops in ((2024, 0.70), (2025, 0.70 + change)):
            rows.append(
                {
                    "player_id": player_id,
                    "player_name": f"타자 {player_id}",
                    "season": season,
                    "team": "KIA",
                    "age": 20 + player_id + season - 2024,
                    "plate_appearances": 400,
                    "batting_average": ops / 3,
                    "on_base_percentage": ops / 2,
                    "slugging_percentage": ops / 2,
                    "on_base_plus_slugging": ops,
                    "home_runs": 10,
                    "runs_batted_in": 50,
                    "stolen_bases": 5,
                    "walks": 30,
                    "strikeouts": 70,
                }
            )
    return pd.DataFrame(rows)


def _pitching_population() -> pd.DataFrame:
    era_changes = [2.0, 1.0, 0.0, -1.0, -2.0]
    rows = []
    for player_id, change in enumerate(era_changes, start=1):
        for season, era in ((2024, 5.0), (2025, 5.0 + change)):
            rows.append(
                {
                    "player_id": player_id,
                    "player_name": f"투수 {player_id}",
                    "season": season,
                    "team": "LG",
                    "age": 25 + player_id + season - 2024,
                    "innings_pitched_outs": 300,
                    "earned_run_average": era,
                    "strikeouts": 100,
                    "walks_allowed": 30,
                    "saves": 0,
                    "holds": 0,
                }
            )
    return pd.DataFrame(rows)


def test_top_decile_ops_change_is_detected_as_breakout() -> None:
    analyzer = PlayerGrowthAnalyzer({"batting": _batting_population()})

    result = analyzer.analyze("batting", 5, ["on_base_plus_slugging"])
    season_2025 = result.curves.loc[result.curves["season"] == 2025].iloc[0]

    assert season_2025["event"] == "breakout"
    assert season_2025["growth_rate_pct"] == pytest.approx(28.5714, rel=1e-4)
    assert result.summary.iloc[0]["best_season"] == 2025
    assert result.summary.iloc[0]["breakout_seasons"] == [2025]
    thresholds = analyzer.league_change_thresholds("batting", ["on_base_plus_slugging"])
    assert thresholds.iloc[0]["sample_count"] == 5


def test_lower_era_is_treated_as_positive_growth() -> None:
    analyzer = PlayerGrowthAnalyzer({"pitching": _pitching_population()})

    result = analyzer.analyze("pitching", 5, ["earned_run_average"])
    season_2025 = result.curves.loc[result.curves["season"] == 2025].iloc[0]

    assert season_2025["absolute_change"] == -2.0
    assert season_2025["performance_change"] == 2.0
    assert season_2025["performance_growth_rate_pct"] == 40.0
    assert season_2025["event"] == "breakout"


def test_unknown_metric_is_rejected() -> None:
    analyzer = PlayerGrowthAnalyzer({"batting": _batting_population()})

    with pytest.raises(ValueError, match="지원하지 않는 지표"):
        analyzer.analyze("batting", 1, ["unknown_metric"])


def test_non_consecutive_season_is_not_classified() -> None:
    frame = _batting_population()
    frame.loc[(frame["player_id"] == 5) & (frame["season"] == 2025), "season"] = 2026
    analyzer = PlayerGrowthAnalyzer({"batting": frame})

    result = analyzer.analyze("batting", 5, ["on_base_plus_slugging"])
    season_2026 = result.curves.loc[result.curves["season"] == 2026].iloc[0]

    assert season_2026["event"] == "not_evaluated"
    assert season_2026["evaluation_status"] == "non_consecutive_season"


def test_small_sample_is_visible_but_excluded_from_best_season() -> None:
    frame = _batting_population()
    current = (frame["player_id"] == 5) & (frame["season"] == 2025)
    frame.loc[current, "plate_appearances"] = 50
    frame.loc[current, "on_base_plus_slugging"] = 1.50
    analyzer = PlayerGrowthAnalyzer({"batting": frame})

    result = analyzer.analyze("batting", 5, ["on_base_plus_slugging"])
    season_2025 = result.curves.loc[result.curves["season"] == 2025].iloc[0]

    assert not bool(season_2025["is_qualified_season"])
    assert season_2025["evaluation_status"] == "insufficient_sample"
    assert result.summary.iloc[0]["best_season"] == 2024
