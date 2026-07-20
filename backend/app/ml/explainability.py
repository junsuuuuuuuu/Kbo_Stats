"""최종 tree model의 global SHAP feature importance 생성."""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline

from app.ml.config import RANDOM_STATE


def global_shap_importance(
    pipeline: Pipeline, features: pd.DataFrame, sample_size: int = 300
) -> list[dict[str, float | str]]:
    """재현 가능한 표본에서 평균 절대 SHAP 값을 계산해 내림차순 반환한다."""

    if features.empty:
        return []
    sample = features.sample(n=min(sample_size, len(features)), random_state=RANDOM_STATE)
    preprocessor = pipeline.named_steps["preprocessor"]
    estimator = pipeline.named_steps["estimator"]
    transformed = preprocessor.transform(sample)
    feature_names = preprocessor.get_feature_names_out()

    explainer = shap.TreeExplainer(estimator)
    shap_values = np.asarray(explainer.shap_values(transformed))
    if shap_values.ndim != 2:
        raise ValueError(f"예상하지 못한 SHAP shape입니다: {shap_values.shape}")
    importance = np.abs(shap_values).mean(axis=0)
    order = np.argsort(importance)[::-1]
    return [
        {"feature": str(feature_names[index]), "mean_abs_shap": float(importance[index])}
        for index in order
    ]
