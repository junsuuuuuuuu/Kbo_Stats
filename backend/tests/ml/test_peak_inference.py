"""저장된 전성기 모델의 checksum, 추론, 도메인 제약 smoke test."""

from app.ml.peak_config import PEAK_ROLE_SPECS, PEAK_TARGET_SPECS
from app.ml.peak_features import build_peak_dataset, load_peak_role_data
from app.ml.peak_inference import PeakPredictor


def test_all_peak_artifacts_pass_checksum_validation() -> None:
    predictor = PeakPredictor()

    loaded = [predictor.load(model_key) for model_key in PEAK_TARGET_SPECS]

    assert len(loaded) == 6


def test_active_batter_peak_prediction_respects_early_peak() -> None:
    frame = load_peak_role_data("batting")
    dataset = build_peak_dataset(frame, PEAK_ROLE_SPECS["batting"], completed_only=False)
    active = dataset.metadata.loc[dataset.metadata["latest_season"] >= 2023].iloc[0]
    player_id = int(active["player_id"])
    feature = dataset.features.loc[active.name]

    result = PeakPredictor().predict_player("batting", player_id, frame)

    assert result["predictions"]["peak_ops"] >= feature["on_base_plus_slugging_max_3"]
    assert result["predictions"]["peak_home_runs"] >= feature["home_runs_max_3"]
    assert 18 <= result["predictions"]["peak_age"] <= 45
    assert result["model_details"]["peak_home_runs"]["uses_baseline_fallback"] is True
    assert result["predictions"]["peak_home_runs"] == feature["home_runs_max_3"]
