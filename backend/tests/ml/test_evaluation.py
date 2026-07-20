"""예측 후처리와 지표 계산 테스트."""

import numpy as np

from app.ml.config import TARGET_SPECS
from app.ml.evaluation import clip_predictions, regression_metrics


def test_rate_prediction_is_clipped_to_domain() -> None:
    spec = TARGET_SPECS["batting_average"]

    clipped = clip_predictions(np.array([-0.2, 0.3, 1.2]), spec)

    assert clipped.tolist() == [0.0, 0.3, 1.0]


def test_regression_metrics_include_required_metrics() -> None:
    metrics = regression_metrics(np.array([1.0, 2.0]), np.array([1.0, 3.0]))

    assert set(metrics) == {"mae", "rmse", "r2", "sample_count"}
    assert metrics["sample_count"] == 2
