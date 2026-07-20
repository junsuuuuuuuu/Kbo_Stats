"""저장된 다음 시즌 Pipeline을 검증하고 예측하는 framework 비종속 서비스."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from app.ml.artifacts import file_sha256
from app.ml.config import ARTIFACT_ROOT, MODEL_VERSION, TARGET_SPECS, TargetSpec
from app.ml.evaluation import clip_predictions
from app.ml.features import build_inference_dataset, load_role_data


@dataclass(frozen=True, slots=True)
class LoadedModel:
    """검증된 Pipeline과 모델 metadata."""

    pipeline: Pipeline
    metadata: dict
    spec: TargetSpec


class NextSeasonPredictor:
    """target별 artifact를 lazy load하고 프로세스 안에서 재사용한다."""

    def __init__(self, version: str = MODEL_VERSION) -> None:
        self._version = version
        self._models: dict[str, LoadedModel] = {}
        self._prediction_cache: dict[tuple[str, int], pd.DataFrame] = {}
        self._lock = RLock()

    def _artifact_directory(self, spec: TargetSpec) -> Path:
        return ARTIFACT_ROOT / spec.key / self._version

    def load(self, target_name: str) -> LoadedModel:
        """metadata 계약과 checksum을 확인한 뒤 Pipeline을 한 번만 로드한다."""

        with self._lock:
            if target_name in self._models:
                return self._models[target_name]
        try:
            spec = TARGET_SPECS[target_name]
        except KeyError as exception:
            raise ValueError(f"지원하지 않는 예측 target입니다: {target_name}") from exception

        directory = self._artifact_directory(spec)
        metadata_path = directory / "metadata.json"
        pipeline_path = directory / "pipeline.joblib"
        if not metadata_path.exists() or not pipeline_path.exists():
            raise FileNotFoundError(f"모델 artifact가 없습니다: {spec.key}/{self._version}")

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata["target"] != target_name or metadata["version"] != self._version:
            raise ValueError("artifact metadata의 target/version 계약이 일치하지 않습니다.")
        actual_checksum = file_sha256(pipeline_path)
        expected_checksum = metadata["artifact"]["pipeline_sha256"]
        if actual_checksum != expected_checksum:
            raise ValueError("pipeline checksum이 일치하지 않습니다.")

        loaded = LoadedModel(joblib.load(pipeline_path), metadata, spec)
        with self._lock:
            self._models[target_name] = loaded
        return loaded

    def predict_season(
        self, target_name: str, base_season: int, frame: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """연속 3년 기록이 있는 선수들의 다음 시즌 예측 DataFrame을 반환한다."""

        cache_key = (target_name, base_season)
        if frame is None:
            with self._lock:
                cached = self._prediction_cache.get(cache_key)
                if cached is not None:
                    return cached.copy()

        loaded = self.load(target_name)
        precomputed_path = self._artifact_directory(loaded.spec) / "predictions_2026.csv"
        if frame is None and base_season == 2025 and precomputed_path.exists():
            result = pd.read_csv(precomputed_path, low_memory=False).rename(
                columns={"season": "base_season"}
            )
            expected_columns = [
                "player_id",
                "player_name",
                "base_season",
                "target_season",
                "prediction",
                "previous_season_value",
            ]
            result = result[expected_columns]
            with self._lock:
                self._prediction_cache[cache_key] = result.copy()
            return result

        source_frame = frame if frame is not None else load_role_data(loaded.spec)
        dataset = build_inference_dataset(source_frame, loaded.spec, base_season)
        if dataset.features.empty:
            return pd.DataFrame(
                columns=[
                    "player_id",
                    "player_name",
                    "base_season",
                    "target_season",
                    "prediction",
                    "previous_season_value",
                ]
            )

        prediction = clip_predictions(loaded.pipeline.predict(dataset.features), loaded.spec)
        result = dataset.metadata[["player_id", "player_name", "target_season"]].copy()
        result.insert(2, "base_season", base_season)
        result["prediction"] = prediction
        result["previous_season_value"] = dataset.baseline.to_numpy()
        if frame is None:
            with self._lock:
                self._prediction_cache[cache_key] = result.copy()
        return result
