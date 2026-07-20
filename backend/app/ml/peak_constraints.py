"""전성기 학습과 온라인 추론이 공유하는 출력 제약."""

import numpy as np

from app.ml.peak_config import PeakTargetSpec


def constrain_peak_predictions(
    values: np.ndarray, baselines: np.ndarray, spec: PeakTargetSpec
) -> np.ndarray:
    """물리 범위와 '커리어 peak는 초기 peak보다 나쁠 수 없음' 계약을 적용한다."""

    constrained = np.clip(values, spec.prediction_min, spec.prediction_max)
    if spec.baseline_relation == "at_least":
        constrained = np.maximum(constrained, baselines)
    elif spec.baseline_relation == "at_most":
        constrained = np.minimum(constrained, baselines)
    return constrained
