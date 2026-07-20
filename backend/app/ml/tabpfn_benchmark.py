"""Python 3.13 격리 환경에서 실행하는 TabPFN CPU benchmark.

TabPFN 2.2는 scikit-learn < 1.7을 요구하므로 기본 Python 3.14 학습 환경과 분리한다.
이 모듈은 배포 artifact 선택이 아니라 동일 walk-forward fold의 성능 비교만 담당한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

from app.ml.artifacts import write_json
from app.ml.config import RANDOM_STATE, REPORT_ROOT, TARGET_SPECS, VALIDATION_YEARS, TargetSpec
from app.ml.features import FeatureDataset, build_training_dataset, load_role_data

MAX_TRAIN_SAMPLES = 1_000
N_ESTIMATORS = 1


@dataclass(frozen=True, slots=True)
class EncodedFold:
    """train 기준으로 결측/범주를 인코딩한 TabPFN 입력."""

    train_features: np.ndarray
    validation_features: np.ndarray
    categorical_indices: list[int]


def encode_fold(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    numeric_features: list[str],
    categorical_features: list[str],
) -> EncodedFold:
    """validation 통계를 보지 않고 median과 category mapping을 학습한다."""

    train_parts: list[np.ndarray] = []
    validation_parts: list[np.ndarray] = []
    for column in numeric_features:
        median = float(train[column].median())
        train_parts.append(train[column].fillna(median).to_numpy(dtype=np.float32)[:, None])
        validation_parts.append(
            validation[column].fillna(median).to_numpy(dtype=np.float32)[:, None]
        )

    categorical_indices: list[int] = []
    for column in categorical_features:
        values = sorted(str(value) for value in train[column].dropna().unique())
        mapping = {value: index for index, value in enumerate(values)}
        train_encoded = train[column].astype(str).map(mapping).fillna(-1)
        validation_encoded = validation[column].astype(str).map(mapping).fillna(-1)
        categorical_indices.append(len(train_parts))
        train_parts.append(train_encoded.to_numpy(dtype=np.float32)[:, None])
        validation_parts.append(validation_encoded.to_numpy(dtype=np.float32)[:, None])

    return EncodedFold(
        train_features=np.hstack(train_parts),
        validation_features=np.hstack(validation_parts),
        categorical_indices=categorical_indices,
    )


def metrics(actual: np.ndarray, prediction: np.ndarray) -> dict[str, float | int]:
    """기본 모델과 같은 MAE/RMSE/R² 계약을 사용한다."""

    return {
        "mae": float(mean_absolute_error(actual, prediction)),
        "rmse": float(root_mean_squared_error(actual, prediction)),
        "r2": float(r2_score(actual, prediction)),
        "sample_count": len(actual),
    }


def clip_prediction(prediction: np.ndarray, spec: TargetSpec) -> np.ndarray:
    """회귀값을 target 도메인으로 제한한다."""

    return np.clip(prediction, spec.prediction_min, spec.prediction_max)


def evaluate_target(spec: TargetSpec, dataset: FeatureDataset) -> dict[str, Any]:
    """동일한 2021~2025 fold에서 최대 1,000개 train 표본으로 TabPFN을 평가한다."""

    from tabpfn import TabPFNRegressor

    years = dataset.metadata["target_season"]
    all_actual: list[np.ndarray] = []
    all_prediction: list[np.ndarray] = []
    fold_metrics: list[dict[str, float | int]] = []

    for validation_year in VALIDATION_YEARS:
        train_indices = dataset.features.index[years < validation_year]
        validation_indices = dataset.features.index[years == validation_year]
        if len(train_indices) == 0 or len(validation_indices) == 0:
            continue
        if len(train_indices) > MAX_TRAIN_SAMPLES:
            train_indices = (
                pd.Series(train_indices)
                .sample(n=MAX_TRAIN_SAMPLES, random_state=RANDOM_STATE + validation_year)
                .to_numpy()
            )

        encoded = encode_fold(
            dataset.features.loc[train_indices],
            dataset.features.loc[validation_indices],
            dataset.numeric_features,
            dataset.categorical_features,
        )
        model = TabPFNRegressor(
            n_estimators=N_ESTIMATORS,
            categorical_features_indices=encoded.categorical_indices,
            device="cpu",
            ignore_pretraining_limits=True,
            n_jobs=1,
            random_state=RANDOM_STATE,
        )
        model.fit(encoded.train_features, dataset.target.loc[train_indices].to_numpy())
        prediction = clip_prediction(model.predict(encoded.validation_features), spec)
        actual = dataset.target.loc[validation_indices].to_numpy()
        baseline = dataset.baseline.loc[validation_indices].to_numpy()
        common = ~np.isnan(baseline)
        actual = actual[common]
        prediction = prediction[common]
        current_metrics = metrics(actual, prediction)
        fold_metrics.append({"validation_year": validation_year, **current_metrics})
        all_actual.append(actual)
        all_prediction.append(prediction)

    actual = np.concatenate(all_actual)
    prediction = np.concatenate(all_prediction)
    return {
        "model_name": "tabpfn",
        "parameters": {
            "n_estimators": N_ESTIMATORS,
            "device": "cpu",
            "max_train_samples": MAX_TRAIN_SAMPLES,
        },
        "metrics": metrics(actual, prediction),
        "fold_metrics": fold_metrics,
        "benchmark_only": True,
    }


def run_benchmark(target_names: list[str]) -> dict[str, Any]:
    """선택 target을 평가하고 기본 학습 보고서에도 비교 결과를 병합한다."""

    import tabpfn
    import torch

    target_results: dict[str, Any] = {}
    for target_name in target_names:
        spec = TARGET_SPECS[target_name]
        print(f"[{spec.key}] TabPFN benchmark 시작", flush=True)
        dataset = build_training_dataset(load_role_data(spec), spec)
        target_results[target_name] = evaluate_target(spec, dataset)
        print(
            f"[{spec.key}] TabPFN MAE={target_results[target_name]['metrics']['mae']:.4f}",
            flush=True,
        )

    report: dict[str, Any] = {
        "runtime": {
            "python": __import__("platform").python_version(),
            "tabpfn": tabpfn.__version__,
            "torch": torch.__version__,
            "cuda": torch.cuda.is_available(),
        },
        "limitations": {
            "benchmark_only": True,
            "reason": "Python 3.13 격리 CPU 환경이며 배포 pipeline과 호환되지 않음",
            "n_estimators": N_ESTIMATORS,
            "max_train_samples": MAX_TRAIN_SAMPLES,
        },
        "targets": target_results,
    }
    write_json(REPORT_ROOT / "tabpfn_benchmark.json", report)

    main_report_path = REPORT_ROOT / "next_season_training_report.json"
    main_report = json.loads(main_report_path.read_text(encoding="utf-8"))
    for target in main_report["targets"]:
        tabpfn_result = target_results.get(target["target"])
        if tabpfn_result is None:
            continue
        models = [
            model for model in target["evaluation"]["models"] if model["model_name"] != "tabpfn"
        ]
        models.append(tabpfn_result)
        target["evaluation"]["models"] = models
    write_json(main_report_path, main_report)
    return report
