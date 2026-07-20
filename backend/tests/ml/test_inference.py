"""학습 artifact의 checksum과 실제 2026 추론 smoke test."""

from app.ml.inference import NextSeasonPredictor


def test_saved_model_predicts_2026_candidates() -> None:
    predictor = NextSeasonPredictor()

    prediction = predictor.predict_season("batting_average", 2025)

    assert len(prediction) == 186
    assert prediction["target_season"].eq(2026).all()
    assert prediction["prediction"].between(0, 1).all()


def test_model_is_cached_after_checksum_validation() -> None:
    predictor = NextSeasonPredictor()

    first = predictor.load("home_runs")
    second = predictor.load("home_runs")

    assert first is second
