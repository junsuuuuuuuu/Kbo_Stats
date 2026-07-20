"""다음 시즌 feature 생성의 시간 누수 방지 테스트."""

from dataclasses import replace

import pandas as pd

from app.ml.config import TARGET_SPECS
from app.ml.features import build_inference_dataset, build_training_dataset


def batting_frame(seasons: list[int]) -> pd.DataFrame:
    """시즌 값 자체를 지표값으로 사용해 lag 방향을 쉽게 검증한다."""

    spec = TARGET_SPECS["batting_average"]
    rows = []
    for season in seasons:
        row = {
            "player_id": 1,
            "player_name": "테스트선수",
            "season": season,
            "team": "KIA",
            "position": "3B",
        }
        row.update({metric: float(season) for metric in spec.numeric_metrics})
        row["batting_average"] = season / 10_000
        row["plate_appearances"] = 200
        rows.append(row)
    return pd.DataFrame(rows)


def test_training_features_use_only_three_past_seasons() -> None:
    spec = replace(TARGET_SPECS["batting_average"], minimum_target_opportunity=0)
    dataset = build_training_dataset(batting_frame([2018, 2019, 2020, 2021]), spec)

    assert len(dataset.features) == 1
    row = dataset.features.iloc[0]
    assert row["games_lag_0"] == 2020
    assert row["games_lag_1"] == 2019
    assert row["games_lag_2"] == 2018
    assert dataset.metadata.iloc[0]["target_season"] == 2021
    assert dataset.target.iloc[0] == 0.2021
    assert "player_id" not in dataset.features.columns


def test_nonconsecutive_history_is_excluded() -> None:
    spec = replace(TARGET_SPECS["batting_average"], minimum_target_opportunity=0)
    dataset = build_training_dataset(batting_frame([2018, 2020, 2021, 2022]), spec)

    assert dataset.features.empty


def test_inference_does_not_require_future_target() -> None:
    spec = TARGET_SPECS["batting_average"]
    dataset = build_inference_dataset(batting_frame([2023, 2024, 2025]), spec, 2025)

    assert len(dataset.features) == 1
    assert dataset.target.isna().all()
    assert dataset.metadata.iloc[0]["target_season"] == 2026
