"""시간 순서를 보존하는 tuning, walk-forward 평가와 지표 계산."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline

from app.ml.config import TUNING_YEAR, VALIDATION_YEARS, TargetSpec
from app.ml.features import FeatureDataset
from app.ml.models import build_pipeline, tuning_candidates


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """한 모델의 선택 parameter와 전체/fold 평가 결과."""

    model_name: str
    parameters: dict[str, Any]
    metrics: dict[str, float | int | None]
    fold_metrics: list[dict[str, float | int | None]]


def clip_predictions(values: np.ndarray, spec: TargetSpec) -> np.ndarray:
    """야구 지표의 물리적 범위를 벗어난 회귀 예측을 평가/서비스 전에 제한한다."""

    return np.clip(values, spec.prediction_min, spec.prediction_max)


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float | int]:
    """요구된 MAE, RMSE, R²와 표본 수를 동일 기준으로 계산한다."""

    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(root_mean_squared_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
        "sample_count": int(len(actual)),
    }


def tune_model(model_name: str, dataset: FeatureDataset, spec: TargetSpec) -> dict[str, Any]:
    """미래 test fold와 분리된 2020 holdout에서 MAE가 낮은 parameter를 선택한다."""

    target_years = dataset.metadata["target_season"]
    train_mask = target_years < TUNING_YEAR
    validation_mask = target_years == TUNING_YEAR
    if not train_mask.any() or not validation_mask.any():
        return tuning_candidates(model_name)[0]

    best_parameters: dict[str, Any] | None = None
    best_mae = float("inf")
    for parameters in tuning_candidates(model_name):
        pipeline = build_pipeline(
            model_name,
            parameters,
            dataset.numeric_features,
            dataset.categorical_features,
        )
        pipeline.fit(dataset.features.loc[train_mask], dataset.target.loc[train_mask])
        prediction = clip_predictions(pipeline.predict(dataset.features.loc[validation_mask]), spec)
        mae = mean_absolute_error(dataset.target.loc[validation_mask], prediction)
        if mae < best_mae:
            best_mae = float(mae)
            best_parameters = parameters
    if best_parameters is None:
        raise RuntimeError(f"{model_name} tuning 결과가 없습니다.")
    return best_parameters


def evaluate_walk_forward(
    model_name: str,
    parameters: dict[str, Any],
    dataset: FeatureDataset,
    spec: TargetSpec,
) -> EvaluationResult:
    """각 검증 연도의 과거 데이터로만 재학습해 미래 정보 누수를 막는다."""

    target_years = dataset.metadata["target_season"]
    all_actual: list[np.ndarray] = []
    all_prediction: list[np.ndarray] = []
    all_baseline: list[np.ndarray] = []
    fold_metrics: list[dict[str, float | int | None]] = []

    for validation_year in VALIDATION_YEARS:
        train_mask = target_years < validation_year
        validation_mask = target_years == validation_year
        if not train_mask.any() or not validation_mask.any():
            continue

        pipeline = build_pipeline(
            model_name,
            parameters,
            dataset.numeric_features,
            dataset.categorical_features,
        )
        pipeline.fit(dataset.features.loc[train_mask], dataset.target.loc[train_mask])
        prediction = clip_predictions(pipeline.predict(dataset.features.loc[validation_mask]), spec)
        actual = dataset.target.loc[validation_mask].to_numpy()
        baseline = dataset.baseline.loc[validation_mask].to_numpy()

        # baseline이 정의된 동일 표본에서만 model과 baseline을 공정하게 비교한다.
        common_mask = ~np.isnan(baseline)
        actual = actual[common_mask]
        prediction = prediction[common_mask]
        baseline = clip_predictions(baseline[common_mask], spec)
        metrics = regression_metrics(actual, prediction)
        baseline_metrics = regression_metrics(actual, baseline)
        fold_metrics.append(
            {
                "validation_year": validation_year,
                **metrics,
                "baseline_mae": baseline_metrics["mae"],
            }
        )
        all_actual.append(actual)
        all_prediction.append(prediction)
        all_baseline.append(baseline)

    if not all_actual:
        raise RuntimeError(f"{spec.key}에 평가 가능한 walk-forward fold가 없습니다.")
    actual = np.concatenate(all_actual)
    prediction = np.concatenate(all_prediction)
    baseline = np.concatenate(all_baseline)
    metrics = regression_metrics(actual, prediction)
    baseline_metrics = regression_metrics(actual, baseline)
    metrics.update(
        {
            "baseline_mae": baseline_metrics["mae"],
            "baseline_rmse": baseline_metrics["rmse"],
            "baseline_r2": baseline_metrics["r2"],
        }
    )
    return EvaluationResult(model_name, parameters, metrics, fold_metrics)


def fit_final_pipeline(result: EvaluationResult, dataset: FeatureDataset) -> Pipeline:
    """평가가 끝난 parameter로 2025 target까지의 모든 label을 사용해 최종 학습한다."""

    pipeline = build_pipeline(
        result.model_name,
        result.parameters,
        dataset.numeric_features,
        dataset.categorical_features,
    )
    pipeline.fit(dataset.features, dataset.target)
    return pipeline


def result_to_dict(result: EvaluationResult) -> dict[str, Any]:
    """dataclass 결과를 JSON 직렬화 가능한 모델 카드 일부로 변환한다."""

    return {
        "model_name": result.model_name,
        "parameters": result.parameters,
        "metrics": result.metrics,
        "fold_metrics": result.fold_metrics,
    }
