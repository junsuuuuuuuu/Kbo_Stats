"""모델 pipeline, metadata, 설명 결과를 버전 디렉터리에 저장한다."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
from sklearn.pipeline import Pipeline


def file_sha256(path: Path) -> str:
    """학습 데이터와 artifact의 변경을 추적할 SHA-256을 계산한다."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    """한국어 metadata를 보존하는 읽기 쉬운 JSON을 저장한다."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_pipeline(path: Path, pipeline: Pipeline) -> str:
    """전처리기와 estimator를 하나의 artifact로 저장하고 checksum을 반환한다."""

    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, path, compress=3)
    return file_sha256(path)
