"""저장된 전성기 residual 모델을 검증하고 선수 단위로 추론한다."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from typing import Any

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from app.ml.artifacts import file_sha256
from app.ml.peak_config import (
    PEAK_ARTIFACT_ROOT,
    PEAK_MODEL_VERSION,
    PEAK_ROLE_SPECS,
    PEAK_TARGET_SPECS,
    PeakTargetSpec,
)
from app.ml.peak_constraints import constrain_peak_predictions
from app.ml.peak_features import build_peak_dataset, load_peak_role_data


@dataclass(frozen=True, slots=True)
class LoadedPeakModel:
    """checksum 검증을 마친 pipeline과 metadata."""

    pipeline: Pipeline
    metadata: dict[str, Any]
    spec: PeakTargetSpec


class PeakPredictor:
    """target 모델을 lazy load하고 동일한 초기 커리어 전처리로 추론한다."""

    def __init__(self, version: str = PEAK_MODEL_VERSION) -> None:
        self._version = version
        self._models: dict[str, LoadedPeakModel] = {}
        self._datasets: dict[str, Any] = {}
        self._prediction_cache: dict[tuple[str, int], dict[str, object]] = {}
        self._lock = RLock()

    @staticmethod
    def _evaluation_policy(loaded: LoadedPeakModel) -> dict[str, object]:
        """검증 MAE가 naive baseline보다 나쁘면 안전한 baseline을 배포한다."""

        selected_model = str(loaded.metadata["selected_model"])
        evaluations = loaded.metadata.get("evaluation", {}).get("models", [])
        selected = next(
            (item for item in evaluations if item.get("model_name") == selected_model),
            None,
        )
        metrics = selected.get("metrics", {}) if selected else {}
        model_mae = metrics.get("mae")
        baseline_mae = metrics.get("baseline_mae")
        uses_baseline = (
            model_mae is not None
            and baseline_mae is not None
            and float(model_mae) >= float(baseline_mae)
        )
        return {
            "deployed_model": "naive_baseline" if uses_baseline else selected_model,
            "candidate_model": selected_model,
            "validation_mae": None if model_mae is None else float(model_mae),
            "baseline_mae": None if baseline_mae is None else float(baseline_mae),
            "uses_baseline_fallback": uses_baseline,
        }

    def load(self, model_key: str) -> LoadedPeakModel:
        with self._lock:
            if model_key in self._models:
                return self._models[model_key]
        try:
            spec = PEAK_TARGET_SPECS[model_key]
        except KeyError as exception:
            raise ValueError(f"지원하지 않는 전성기 모델입니다: {model_key}") from exception

        directory = PEAK_ARTIFACT_ROOT / model_key / self._version
        metadata_path = directory / "metadata.json"
        pipeline_path = directory / "pipeline.joblib"
        if not metadata_path.exists() or not pipeline_path.exists():
            raise FileNotFoundError(f"전성기 모델 artifact가 없습니다: {model_key}/{self._version}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata["model_key"] != model_key or metadata["version"] != self._version:
            raise ValueError("전성기 artifact의 model key/version 계약이 일치하지 않습니다.")
        if file_sha256(pipeline_path) != metadata["artifact"]["pipeline_sha256"]:
            raise ValueError("전성기 pipeline checksum이 일치하지 않습니다.")

        loaded = LoadedPeakModel(joblib.load(pipeline_path), metadata, spec)
        with self._lock:
            self._models[model_key] = loaded
        return loaded

    def predict_player(
        self,
        role: str,
        player_id: int,
        frame: pd.DataFrame | None = None,
    ) -> dict[str, object]:
        """유효 시즌 3년 이상인 선수의 Peak Age와 역할별 peak 기록을 반환한다."""

        if role not in PEAK_ROLE_SPECS:
            raise ValueError(f"지원하지 않는 선수 역할입니다: {role}")
        cache_key = (role, player_id)
        if frame is None:
            with self._lock:
                cached = self._prediction_cache.get(cache_key)
                if cached is not None:
                    return deepcopy(cached)
                dataset = self._datasets.get(role)
            if dataset is None:
                source = load_peak_role_data(role)
                dataset = build_peak_dataset(source, PEAK_ROLE_SPECS[role], completed_only=False)
                with self._lock:
                    self._datasets[role] = dataset
        else:
            dataset = build_peak_dataset(frame, PEAK_ROLE_SPECS[role], completed_only=False)
        matched = dataset.metadata["player_id"] == player_id
        if not matched.any():
            raise ValueError(f"전성기 예측에 필요한 유효 시즌 3년이 없습니다: {player_id}")
        row_index = dataset.metadata.index[matched][0]
        feature_row = dataset.features.loc[[row_index]]
        metadata = dataset.metadata.loc[row_index]

        predictions: dict[str, float] = {}
        model_details: dict[str, dict[str, object]] = {}
        for model_key, target_spec in PEAK_TARGET_SPECS.items():
            if target_spec.role != role:
                continue
            loaded = self.load(model_key)
            baseline = feature_row[target_spec.baseline_feature].to_numpy(dtype=float)
            policy = self._evaluation_policy(loaded)
            if policy["uses_baseline_fallback"]:
                prediction = baseline
            else:
                prediction = constrain_peak_predictions(
                    loaded.pipeline.predict(feature_row) + baseline,
                    baseline,
                    target_spec,
                )
            predictions[target_spec.target] = float(prediction[0])
            model_details[target_spec.target] = policy

        peak_age = predictions["peak_age"]
        current_age = metadata["current_age"]
        if pd.isna(current_age):
            timing = "unknown"
        elif peak_age > float(current_age) + 0.5:
            timing = "future"
        else:
            timing = "past_or_current"
        result: dict[str, object] = {
            "player_id": player_id,
            "player_name": str(metadata["player_name"]),
            "role": role,
            "current_age": None if pd.isna(current_age) else float(current_age),
            "feature_cutoff_season": int(metadata["feature_cutoff_season"]),
            "qualified_season_count": int(metadata["qualified_season_count"]),
            "peak_timing": timing,
            "predictions": predictions,
            "model_details": model_details,
        }
        if frame is None:
            with self._lock:
                self._prediction_cache[cache_key] = deepcopy(result)
        return result
