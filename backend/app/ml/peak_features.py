"""초기 3개 유효 시즌에서 누수 없는 전성기 예측 feature와 label을 생성한다."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.ml.peak_config import (
    COMPLETED_CAREER_LAST_SEASON,
    EARLY_CAREER_SEASONS,
    MINIMUM_CAREER_SEASONS,
    PEAK_ROLE_SPECS,
    PeakRoleSpec,
)


@dataclass(frozen=True, slots=True)
class PeakDataset:
    """모델 feature, 역할별 label, 선수 추적 metadata를 분리한다."""

    features: pd.DataFrame
    targets: pd.DataFrame
    metadata: pd.DataFrame
    numeric_features: list[str]
    categorical_features: list[str]


def load_peak_role_data(role: str) -> pd.DataFrame:
    try:
        spec = PEAK_ROLE_SPECS[role]
    except KeyError as exception:
        raise ValueError(f"지원하지 않는 선수 역할입니다: {role}") from exception
    return pd.read_csv(spec.source_path, low_memory=False)


def peak_feature_names(spec: PeakRoleSpec) -> tuple[list[str], list[str]]:
    numeric = [
        "debut_season",
        "debut_age",
        "feature_cutoff_age",
        "early_career_season_span",
    ]
    for metric in spec.numeric_metrics:
        if metric == "age":
            continue
        numeric.extend(f"{metric}_season_{index}" for index in range(1, 4))
        numeric.extend(
            (
                f"{metric}_mean_3",
                f"{metric}_trend_3",
                f"{metric}_min_3",
                f"{metric}_max_3",
            )
        )
    return numeric, list(spec.categorical_features)


def _validate_columns(frame: pd.DataFrame, spec: PeakRoleSpec) -> None:
    required = {
        "player_id",
        "player_name",
        "season",
        "team",
        "age",
        spec.opportunity_column,
        *spec.numeric_metrics,
        *spec.categorical_features,
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"전성기 feature 생성에 필요한 컬럼이 없습니다: {missing}")


def _feature_row(qualified: pd.DataFrame, spec: PeakRoleSpec) -> dict[str, object]:
    early = qualified.iloc[:EARLY_CAREER_SEASONS]
    row: dict[str, object] = {
        "debut_season": int(early.iloc[0]["season"]),
        "debut_age": early.iloc[0]["age"],
        "feature_cutoff_age": early.iloc[-1]["age"],
        "early_career_season_span": int(early.iloc[-1]["season"] - early.iloc[0]["season"]),
    }
    for metric in spec.numeric_metrics:
        if metric == "age":
            continue
        values = pd.to_numeric(early[metric], errors="coerce").reset_index(drop=True)
        for index, value in enumerate(values, start=1):
            row[f"{metric}_season_{index}"] = value
        row[f"{metric}_mean_3"] = values.mean()
        row[f"{metric}_trend_3"] = values.iloc[-1] - values.iloc[0]
        row[f"{metric}_min_3"] = values.min()
        row[f"{metric}_max_3"] = values.max()
    for column in spec.categorical_features:
        row[column] = early.iloc[-1][column]
    return row


def _target_row(qualified: pd.DataFrame, spec: PeakRoleSpec) -> dict[str, float]:
    primary = qualified.dropna(subset=[spec.primary_metric, "age"])
    if primary.empty:
        return {}
    primary_index = (
        primary[spec.primary_metric].idxmax()
        if spec.primary_higher_is_better
        else primary[spec.primary_metric].idxmin()
    )
    peak_age = float(primary.loc[primary_index, "age"])
    if spec.role == "batting":
        return {
            "peak_age": peak_age,
            "peak_ops": float(qualified["on_base_plus_slugging"].max()),
            "peak_home_runs": float(qualified["home_runs"].max()),
        }
    return {
        "peak_age": peak_age,
        "peak_era": float(qualified["earned_run_average"].min()),
        "peak_strikeouts": float(qualified["strikeouts"].max()),
    }


def build_peak_dataset(
    frame: pd.DataFrame,
    spec: PeakRoleSpec,
    *,
    completed_only: bool,
) -> PeakDataset:
    """선수당 하나의 초기 커리어 표본을 만들고 완료 커리어에만 label을 부여한다."""

    _validate_columns(frame, spec)
    feature_rows: list[dict[str, object]] = []
    target_rows: list[dict[str, float]] = []
    metadata_rows: list[dict[str, object]] = []

    for player_id, career in frame.groupby("player_id", sort=False):
        career = career.sort_values("season")
        qualified = career.loc[career[spec.opportunity_column].ge(spec.minimum_opportunity)].copy()
        minimum_seasons = MINIMUM_CAREER_SEASONS if completed_only else EARLY_CAREER_SEASONS
        if len(qualified) < minimum_seasons:
            continue
        if completed_only and int(career["season"].max()) > COMPLETED_CAREER_LAST_SEASON:
            continue
        targets = _target_row(qualified, spec) if completed_only else {}
        if completed_only and not targets:
            continue

        feature_rows.append(_feature_row(qualified, spec))
        target_rows.append(targets)
        latest = career.iloc[-1]
        metadata_rows.append(
            {
                "player_id": int(player_id),
                "player_name": str(latest["player_name"]),
                "feature_cutoff_season": int(qualified.iloc[EARLY_CAREER_SEASONS - 1]["season"]),
                "latest_season": int(latest["season"]),
                "current_age": None if pd.isna(latest["age"]) else float(latest["age"]),
                "qualified_season_count": len(qualified),
            }
        )

    numeric, categorical = peak_feature_names(spec)
    features = pd.DataFrame(feature_rows).reindex(columns=numeric + categorical)
    targets = pd.DataFrame(target_rows, index=features.index)
    metadata = pd.DataFrame(metadata_rows, index=features.index)
    return PeakDataset(features, targets, metadata, numeric, categorical)
