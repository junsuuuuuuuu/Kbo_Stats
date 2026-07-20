"""전성기 feature의 초기 커리어 제한과 label 생성 테스트."""

import pandas as pd

from app.ml.peak_config import PEAK_ROLE_SPECS
from app.ml.peak_features import build_peak_dataset


def _career_frame(last_season: int = 2004) -> pd.DataFrame:
    spec = PEAK_ROLE_SPECS["batting"]
    rows = []
    ops_values = [0.60, 0.70, 0.80, 1.00, 0.75]
    for index, season in enumerate(range(2000, last_season + 1)):
        row = {metric: 1.0 for metric in spec.numeric_metrics}
        row.update(
            {
                "player_id": 10,
                "player_name": "테스트 타자",
                "season": season,
                "team": "KIA",
                "position": "3B",
                "age": 22 + index,
                "plate_appearances": 400,
                "on_base_plus_slugging": ops_values[index],
                "home_runs": [5, 10, 15, 30, 20][index],
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def test_completed_career_uses_first_three_seasons_for_features() -> None:
    spec = PEAK_ROLE_SPECS["batting"]

    dataset = build_peak_dataset(_career_frame(), spec, completed_only=True)

    assert len(dataset.features) == 1
    assert dataset.features.iloc[0]["on_base_plus_slugging_season_3"] == 0.80
    assert dataset.features.iloc[0]["on_base_plus_slugging_max_3"] == 0.80
    assert dataset.metadata.iloc[0]["feature_cutoff_season"] == 2002
    assert dataset.targets.iloc[0]["peak_age"] == 25
    assert dataset.targets.iloc[0]["peak_ops"] == 1.0
    assert dataset.targets.iloc[0]["peak_home_runs"] == 30


def test_later_season_change_does_not_modify_model_features() -> None:
    spec = PEAK_ROLE_SPECS["batting"]
    original = _career_frame()
    changed = original.copy()
    changed.loc[changed["season"] == 2004, "on_base_plus_slugging"] = 1.50

    first = build_peak_dataset(original, spec, completed_only=True)
    second = build_peak_dataset(changed, spec, completed_only=True)

    pd.testing.assert_frame_equal(first.features, second.features)
    assert first.targets.iloc[0]["peak_ops"] != second.targets.iloc[0]["peak_ops"]


def test_active_player_is_available_only_for_inference() -> None:
    spec = PEAK_ROLE_SPECS["batting"]
    frame = _career_frame()
    frame["season"] = frame["season"] + 21

    training = build_peak_dataset(frame, spec, completed_only=True)
    inference = build_peak_dataset(frame, spec, completed_only=False)

    assert training.features.empty
    assert len(inference.features) == 1
    assert inference.metadata.iloc[0]["latest_season"] == 2025
