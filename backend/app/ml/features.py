"""최근 3년 기록으로 누수 없는 다음 시즌 학습/추론 feature를 생성한다."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.ml.config import HISTORY_YEARS, TargetSpec

META_COLUMNS = ["player_id", "player_name", "season", "target_season"]


@dataclass(frozen=True, slots=True)
class FeatureDataset:
    """모델 입력과 추적용 metadata/target을 명시적으로 분리한다."""

    features: pd.DataFrame
    target: pd.Series
    metadata: pd.DataFrame
    numeric_features: list[str]
    categorical_features: list[str]
    baseline: pd.Series


def load_role_data(spec: TargetSpec) -> pd.DataFrame:
    """정제 CSV를 명시적 nullable 값과 함께 읽는다."""

    return pd.read_csv(spec.source_path)


def _build_all_feature_rows(frame: pd.DataFrame, spec: TargetSpec) -> pd.DataFrame:
    """모든 선수-기준시즌에 lag/평균/추세 및 다음 시즌 label을 붙인다."""

    required = {
        "player_id",
        "player_name",
        "season",
        spec.target,
        spec.opportunity_column,
        *spec.numeric_metrics,
        *spec.categorical_features,
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"feature 생성에 필요한 컬럼이 없습니다: {missing}")

    ordered = frame.sort_values(["player_id", "season"]).reset_index(drop=True).copy()
    grouped = ordered.groupby("player_id", sort=False)
    feature_rows = ordered[["player_id", "player_name", "season"]].copy()
    feature_rows["target_season"] = ordered["season"] + 1

    for feature in spec.numeric_metrics:
        lag_columns: list[str] = []
        for lag in range(HISTORY_YEARS):
            column = f"{feature}_lag_{lag}"
            feature_rows[column] = grouped[feature].shift(lag)
            lag_columns.append(column)
        feature_rows[f"{feature}_mean_{HISTORY_YEARS}y"] = feature_rows[lag_columns].mean(axis=1)
        feature_rows[f"{feature}_trend_{HISTORY_YEARS}y"] = (
            feature_rows[lag_columns[0]] - feature_rows[lag_columns[-1]]
        )

    for feature in spec.categorical_features:
        feature_rows[feature] = ordered[feature]

    # shift(-1)은 반드시 같은 player_id 그룹 안에서만 수행한다.
    feature_rows["_target"] = grouped[spec.target].shift(-1)
    feature_rows["_target_opportunity"] = grouped[spec.opportunity_column].shift(-1)
    feature_rows["_actual_next_season"] = grouped["season"].shift(-1)

    consecutive_history = pd.Series(True, index=ordered.index)
    for lag in range(1, HISTORY_YEARS):
        consecutive_history &= grouped["season"].shift(lag).eq(ordered["season"] - lag)
    feature_rows["_has_consecutive_history"] = consecutive_history
    feature_rows["_has_consecutive_target"] = feature_rows["_actual_next_season"].eq(
        feature_rows["target_season"]
    )
    return feature_rows


def feature_column_names(spec: TargetSpec) -> tuple[list[str], list[str]]:
    """명세에서 numeric/categorical 모델 입력 컬럼을 결정론적으로 생성한다."""

    numeric: list[str] = ["season"]
    for feature in spec.numeric_metrics:
        numeric.extend(f"{feature}_lag_{lag}" for lag in range(HISTORY_YEARS))
        numeric.append(f"{feature}_mean_{HISTORY_YEARS}y")
        numeric.append(f"{feature}_trend_{HISTORY_YEARS}y")
    return numeric, list(spec.categorical_features)


def build_training_dataset(frame: pd.DataFrame, spec: TargetSpec) -> FeatureDataset:
    """연속 3년 history와 유효한 다음 시즌 target이 있는 학습 표본을 만든다."""

    rows = _build_all_feature_rows(frame, spec)
    eligible = (
        rows["_has_consecutive_history"]
        & rows["_has_consecutive_target"]
        & rows["_target"].notna()
        & rows["_target_opportunity"].ge(spec.minimum_target_opportunity)
    )
    rows = rows.loc[eligible].reset_index(drop=True)
    numeric, categorical = feature_column_names(spec)
    selected_features = numeric + categorical
    return FeatureDataset(
        features=rows[selected_features],
        target=rows["_target"].astype(float),
        metadata=rows[META_COLUMNS],
        numeric_features=numeric,
        categorical_features=categorical,
        baseline=rows[f"{spec.target}_lag_0"].astype(float),
    )


def build_inference_dataset(
    frame: pd.DataFrame, spec: TargetSpec, base_season: int
) -> FeatureDataset:
    """target 없이도 연속 3년을 가진 기준 시즌 선수의 추론 입력을 만든다."""

    rows = _build_all_feature_rows(frame, spec)
    eligible = rows["_has_consecutive_history"] & rows["season"].eq(base_season)
    rows = rows.loc[eligible].reset_index(drop=True)
    numeric, categorical = feature_column_names(spec)
    selected_features = numeric + categorical
    empty_target = pd.Series(index=rows.index, dtype=float, name="target")
    return FeatureDataset(
        features=rows[selected_features],
        target=empty_target,
        metadata=rows[META_COLUMNS],
        numeric_features=numeric,
        categorical_features=categorical,
        baseline=rows[f"{spec.target}_lag_0"].astype(float),
    )
