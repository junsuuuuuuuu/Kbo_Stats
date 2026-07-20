"""전성기 target별 시간 코호트 모델 비교, 저장, SHAP 생성 orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline

from app.ml.artifacts import file_sha256, save_pipeline, write_json
from app.ml.config import PROJECT_ROOT
from app.ml.evaluation import regression_metrics
from app.ml.explainability import global_shap_importance
from app.ml.models import MODEL_NAMES, build_pipeline, tuning_candidates
from app.ml.peak_config import (
    COMPLETED_CAREER_LAST_SEASON,
    EARLY_CAREER_SEASONS,
    MINIMUM_CAREER_SEASONS,
    PEAK_ARTIFACT_ROOT,
    PEAK_MODEL_VERSION,
    PEAK_REPORT_PATH,
    PEAK_ROLE_SPECS,
    PEAK_TARGET_SPECS,
    TUNING_COHORT_START,
    VALIDATION_COHORT_START,
    PeakTargetSpec,
)
from app.ml.peak_constraints import constrain_peak_predictions
from app.ml.peak_features import PeakDataset, build_peak_dataset, load_peak_role_data
from app.ml.training import library_versions


@dataclass(frozen=True, slots=True)
class PeakEvaluation:
    """모델별 tuning 성능과 격리된 최신 코호트 평가 결과."""

    model_name: str
    parameters: dict[str, Any]
    tuning_mae: float
    metrics: dict[str, float | int]


def _target_rows(
    dataset: PeakDataset, target_spec: PeakTargetSpec
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    valid = dataset.targets[target_spec.target].notna()
    return (
        dataset.features.loc[valid].reset_index(drop=True),
        dataset.targets.loc[valid, target_spec.target].astype(float).reset_index(drop=True),
        dataset.metadata.loc[valid].reset_index(drop=True),
    )


def _residual_target(
    features: pd.DataFrame, target: pd.Series, target_spec: PeakTargetSpec
) -> pd.Series:
    """초기 3시즌 기준선 이후의 추가 성장분을 학습 target으로 만든다."""

    return target - features[target_spec.baseline_feature].astype(float)


def _mae_parameters(model_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """0이 많은 peak 성장분에 맞춰 학습 손실과 선택 지표 MAE를 일치시킨다."""

    adjusted = parameters.copy()
    if model_name == "random_forest":
        adjusted["criterion"] = "absolute_error"
    elif model_name == "lightgbm":
        adjusted["objective"] = "regression_l1"
    elif model_name == "xgboost":
        adjusted["objective"] = "reg:absoluteerror"
    return adjusted


def _tune_model(
    model_name: str,
    dataset: PeakDataset,
    target_spec: PeakTargetSpec,
) -> tuple[dict[str, Any], float]:
    features, target, metadata = _target_rows(dataset, target_spec)
    cutoff = metadata["feature_cutoff_season"]
    train_mask = cutoff < TUNING_COHORT_START
    tuning_mask = cutoff.between(TUNING_COHORT_START, VALIDATION_COHORT_START - 1)
    if not train_mask.any() or not tuning_mask.any():
        raise RuntimeError(f"{target_spec.key} 시간순 tuning 표본이 부족합니다.")

    best_parameters: dict[str, Any] | None = None
    best_mae = float("inf")
    for base_parameters in tuning_candidates(model_name):
        parameters = _mae_parameters(model_name, base_parameters)
        pipeline = build_pipeline(
            model_name,
            parameters,
            dataset.numeric_features,
            dataset.categorical_features,
        )
        residual = _residual_target(features, target, target_spec)
        pipeline.fit(features.loc[train_mask], residual.loc[train_mask])
        tuning_baseline = features.loc[tuning_mask, target_spec.baseline_feature].to_numpy(
            dtype=float
        )
        prediction = constrain_peak_predictions(
            pipeline.predict(features.loc[tuning_mask]) + tuning_baseline,
            tuning_baseline,
            target_spec,
        )
        mae = float(mean_absolute_error(target.loc[tuning_mask], prediction))
        if mae < best_mae:
            best_mae = mae
            best_parameters = parameters
    if best_parameters is None:
        raise RuntimeError(f"{target_spec.key}/{model_name} tuning 결과가 없습니다.")
    return best_parameters, best_mae


def _evaluate_model(
    model_name: str,
    parameters: dict[str, Any],
    tuning_mae: float,
    dataset: PeakDataset,
    target_spec: PeakTargetSpec,
) -> PeakEvaluation:
    features, target, metadata = _target_rows(dataset, target_spec)
    cutoff = metadata["feature_cutoff_season"]
    train_mask = cutoff < VALIDATION_COHORT_START
    validation_mask = cutoff >= VALIDATION_COHORT_START
    if not train_mask.any() or not validation_mask.any():
        raise RuntimeError(f"{target_spec.key} 최신 코호트 평가 표본이 부족합니다.")

    pipeline = build_pipeline(
        model_name,
        parameters,
        dataset.numeric_features,
        dataset.categorical_features,
    )
    residual = _residual_target(features, target, target_spec)
    pipeline.fit(features.loc[train_mask], residual.loc[train_mask])
    baseline = features.loc[validation_mask, target_spec.baseline_feature].to_numpy(dtype=float)
    prediction = constrain_peak_predictions(
        pipeline.predict(features.loc[validation_mask]) + baseline,
        baseline,
        target_spec,
    )
    actual = target.loc[validation_mask].to_numpy()
    baseline = constrain_peak_predictions(baseline, baseline, target_spec)
    metrics = regression_metrics(actual, prediction)
    baseline_metrics = regression_metrics(actual, baseline)
    metrics.update(
        {
            "baseline_mae": baseline_metrics["mae"],
            "baseline_rmse": baseline_metrics["rmse"],
            "baseline_r2": baseline_metrics["r2"],
        }
    )
    return PeakEvaluation(model_name, parameters, tuning_mae, metrics)


def _fit_final_pipeline(
    evaluation: PeakEvaluation,
    dataset: PeakDataset,
    target_spec: PeakTargetSpec,
) -> tuple[Pipeline, pd.DataFrame]:
    features, target, _ = _target_rows(dataset, target_spec)
    pipeline = build_pipeline(
        evaluation.model_name,
        evaluation.parameters,
        dataset.numeric_features,
        dataset.categorical_features,
    )
    pipeline.fit(features, _residual_target(features, target, target_spec))
    return pipeline, features


def _evaluation_payload(evaluation: PeakEvaluation) -> dict[str, Any]:
    return {
        "model_name": evaluation.model_name,
        "parameters": evaluation.parameters,
        "tuning_mae": evaluation.tuning_mae,
        "metrics": evaluation.metrics,
    }


def train_peak_target(
    target_spec: PeakTargetSpec,
    role_dataset: PeakDataset,
    inference_dataset: PeakDataset,
) -> dict[str, Any]:
    """target 하나를 비교하고 tuning cohort 기준 최종 모델을 선택한다."""

    evaluations = []
    for model_name in MODEL_NAMES:
        parameters, tuning_mae = _tune_model(model_name, role_dataset, target_spec)
        evaluations.append(
            _evaluate_model(model_name, parameters, tuning_mae, role_dataset, target_spec)
        )
    # 최신 검증 코호트는 최종 성능 추정에만 사용하고 모델 선택에는 사용하지 않는다.
    selected = min(evaluations, key=lambda item: item.tuning_mae)
    pipeline, training_features = _fit_final_pipeline(selected, role_dataset, target_spec)
    shap_importance = global_shap_importance(pipeline, training_features)

    artifact_directory = PEAK_ARTIFACT_ROOT / target_spec.key / PEAK_MODEL_VERSION
    pipeline_path = artifact_directory / "pipeline.joblib"
    pipeline_sha256 = save_pipeline(pipeline_path, pipeline)
    write_json(artifact_directory / "shap_importance.json", shap_importance)

    active = inference_dataset.metadata["latest_season"] >= 2023
    active_predictions = inference_dataset.metadata.loc[active].copy()
    active_baseline = inference_dataset.features.loc[active, target_spec.baseline_feature].to_numpy(
        dtype=float
    )
    active_predictions["prediction"] = constrain_peak_predictions(
        pipeline.predict(inference_dataset.features.loc[active]) + active_baseline,
        active_baseline,
        target_spec,
    )
    active_predictions.to_csv(
        artifact_directory / "active_player_predictions.csv", index=False, encoding="utf-8"
    )

    metadata = {
        "model_key": target_spec.key,
        "version": PEAK_MODEL_VERSION,
        "role": target_spec.role,
        "target": target_spec.target,
        "target_label": target_spec.label,
        "selected_model": selected.model_name,
        "selection_rule": "lowest MAE on 2005-2009 tuning cohort",
        "target_transformation": "target minus early-career baseline",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "training": {
            "sample_count": len(training_features),
            "early_career_seasons": EARLY_CAREER_SEASONS,
            "minimum_career_seasons": MINIMUM_CAREER_SEASONS,
            "completed_career_last_season": COMPLETED_CAREER_LAST_SEASON,
            "tuning_cohort_start": TUNING_COHORT_START,
            "validation_cohort_start": VALIDATION_COHORT_START,
            "numeric_features": role_dataset.numeric_features,
            "categorical_features": role_dataset.categorical_features,
        },
        "evaluation": {
            "selection_metric": "tuning_mae",
            "models": [_evaluation_payload(item) for item in evaluations],
        },
        "artifact": {
            "pipeline_path": pipeline_path.relative_to(PROJECT_ROOT).as_posix(),
            "pipeline_sha256": pipeline_sha256,
            "shap_importance_path": (
                artifact_directory / "shap_importance.json"
            ).relative_to(PROJECT_ROOT).as_posix(),
        },
        "libraries": library_versions(),
    }
    write_json(artifact_directory / "metadata.json", metadata)
    return metadata


def train_all_peak_targets() -> list[dict[str, Any]]:
    """역할별 dataset을 한 번 만들고 6개 target artifact와 통합 보고서를 생성한다."""

    role_data = {role: load_peak_role_data(role) for role in PEAK_ROLE_SPECS}
    training_datasets = {
        role: build_peak_dataset(frame, PEAK_ROLE_SPECS[role], completed_only=True)
        for role, frame in role_data.items()
    }
    inference_datasets = {
        role: build_peak_dataset(frame, PEAK_ROLE_SPECS[role], completed_only=False)
        for role, frame in role_data.items()
    }
    results = []
    for target_spec in PEAK_TARGET_SPECS.values():
        print(f"[{target_spec.key}] 학습 시작")
        metadata = train_peak_target(
            target_spec,
            training_datasets[target_spec.role],
            inference_datasets[target_spec.role],
        )
        results.append(metadata)
        selected = next(
            item
            for item in metadata["evaluation"]["models"]
            if item["model_name"] == metadata["selected_model"]
        )
        print(
            f"[{target_spec.key}] 완료: model={metadata['selected_model']}, "
            f"MAE={selected['metrics']['mae']:.4f}"
        )
    write_json(
        PEAK_REPORT_PATH,
        {
            "model_version": PEAK_MODEL_VERSION,
            "sources": {
                role: {
                    "path": spec.source_path.name,
                    "sha256": file_sha256(spec.source_path),
                }
                for role, spec in PEAK_ROLE_SPECS.items()
            },
            "targets": results,
        },
    )
    return results
