"""다음 시즌 target별 모델 비교, 선택, 설명 및 artifact 저장 orchestration."""

from __future__ import annotations

import json
import platform
from datetime import UTC, datetime
from typing import Any

import lightgbm
import numpy as np
import pandas as pd
import shap
import sklearn
import xgboost

from app.ml.artifacts import file_sha256, save_pipeline, write_json
from app.ml.config import (
    ARTIFACT_ROOT,
    HISTORY_YEARS,
    MODEL_VERSION,
    PROJECT_ROOT,
    REPORT_ROOT,
    TUNING_YEAR,
    VALIDATION_YEARS,
    TargetSpec,
)
from app.ml.evaluation import (
    clip_predictions,
    evaluate_walk_forward,
    fit_final_pipeline,
    result_to_dict,
    tune_model,
)
from app.ml.explainability import global_shap_importance
from app.ml.features import build_inference_dataset, build_training_dataset, load_role_data
from app.ml.models import MODEL_NAMES


def library_versions() -> dict[str, str]:
    """artifact 재현에 필요한 실행 환경 버전을 기록한다."""

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
        "lightgbm": lightgbm.__version__,
        "xgboost": xgboost.__version__,
        "shap": shap.__version__,
    }


def train_target(spec: TargetSpec) -> dict[str, Any]:
    """한 target의 세 후보 모델을 같은 fold로 비교하고 최종 artifact를 만든다."""

    frame = load_role_data(spec)
    dataset = build_training_dataset(frame, spec)
    if dataset.features.empty:
        raise RuntimeError(f"{spec.key} 학습 표본이 없습니다.")

    evaluations = []
    for model_name in MODEL_NAMES:
        parameters = tune_model(model_name, dataset, spec)
        result = evaluate_walk_forward(model_name, parameters, dataset, spec)
        evaluations.append(result)

    selected = min(evaluations, key=lambda result: float(result.metrics["mae"]))
    final_pipeline = fit_final_pipeline(selected, dataset)
    shap_importance = global_shap_importance(final_pipeline, dataset.features)

    artifact_directory = ARTIFACT_ROOT / spec.key / MODEL_VERSION
    pipeline_path = artifact_directory / "pipeline.joblib"
    pipeline_sha256 = save_pipeline(pipeline_path, final_pipeline)
    write_json(artifact_directory / "shap_importance.json", shap_importance)

    inference = build_inference_dataset(frame, spec, base_season=2025)
    if not inference.features.empty:
        predictions = clip_predictions(final_pipeline.predict(inference.features), spec)
        prediction_frame = inference.metadata.copy()
        prediction_frame["prediction"] = predictions
        prediction_frame["previous_season_value"] = inference.baseline
        prediction_frame.to_csv(
            artifact_directory / "predictions_2026.csv", index=False, encoding="utf-8"
        )

    metadata: dict[str, Any] = {
        "model_key": spec.key,
        "version": MODEL_VERSION,
        "role": spec.role,
        "target": spec.target,
        "selected_model": selected.model_name,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source": {
            "path": spec.source_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": file_sha256(spec.source_path),
            "season_min": int(frame["season"].min()),
            "season_max": int(frame["season"].max()),
        },
        "training": {
            "history_years": HISTORY_YEARS,
            "sample_count": len(dataset.features),
            "target_season_min": int(dataset.metadata["target_season"].min()),
            "target_season_max": int(dataset.metadata["target_season"].max()),
            "minimum_target_opportunity": spec.minimum_target_opportunity,
            "opportunity_column": spec.opportunity_column,
            "tuning_year": TUNING_YEAR,
            "walk_forward_validation_years": list(VALIDATION_YEARS),
            "numeric_features": dataset.numeric_features,
            "categorical_features": dataset.categorical_features,
        },
        "evaluation": {
            "selection_metric": "mae",
            "models": [result_to_dict(result) for result in evaluations],
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


def train_targets(specs: list[TargetSpec]) -> list[dict[str, Any]]:
    """여러 target을 순차 학습하고 통합 report를 저장한다."""

    results = []
    for spec in specs:
        print(f"[{spec.key}] 학습 시작")
        metadata = train_target(spec)
        results.append(metadata)
        selected = metadata["selected_model"]
        selected_result = next(
            model for model in metadata["evaluation"]["models"] if model["model_name"] == selected
        )
        print(f"[{spec.key}] 완료: model={selected}, MAE={selected_result['metrics']['mae']:.4f}")
    report_path = REPORT_ROOT / "next_season_training_report.json"
    merged_targets: dict[str, dict[str, Any]] = {}
    if report_path.exists():
        previous = json.loads(report_path.read_text(encoding="utf-8"))
        merged_targets.update({item["target"]: item for item in previous.get("targets", [])})
    merged_targets.update({item["target"]: item for item in results})
    ordered_targets = [
        merged_targets[target]
        for target in (
            "batting_average",
            "on_base_plus_slugging",
            "home_runs",
            "earned_run_average",
            "strikeouts",
        )
        if target in merged_targets
    ]
    write_json(
        report_path,
        {"model_version": MODEL_VERSION, "targets": ordered_targets},
    )
    return results
