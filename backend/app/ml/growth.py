"""선수의 연속 시즌 성장률과 급성장·하락 시즌을 분석한다."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.ml.growth_config import (
    BREAKOUT_PERCENTILE,
    DECLINE_PERCENTILE,
    GROWTH_SPECS,
    GrowthMetricSpec,
    GrowthRoleSpec,
)


@dataclass(frozen=True, slots=True)
class GrowthAnalysisResult:
    """선수 정보, Plotly용 long-format 곡선, 주요 이벤트와 지표 요약."""

    player: dict[str, object]
    curves: pd.DataFrame
    events: pd.DataFrame
    summary: pd.DataFrame


class PlayerGrowthAnalyzer:
    """리그 전체 변화 분포와 비교해 한 선수의 커리어 변화를 판정한다."""

    def __init__(self, frames: Mapping[str, pd.DataFrame] | None = None) -> None:
        self._frames = {key: value.copy() for key, value in (frames or {}).items()}
        self._change_distributions: dict[tuple[str, str], np.ndarray] = {}

    @staticmethod
    def _spec(role: str) -> GrowthRoleSpec:
        try:
            return GROWTH_SPECS[role]
        except KeyError as exception:
            raise ValueError(f"지원하지 않는 선수 역할입니다: {role}") from exception

    def _load(self, role: str) -> tuple[pd.DataFrame, GrowthRoleSpec]:
        spec = self._spec(role)
        frame = self._frames.get(role)
        if frame is None:
            frame = pd.read_csv(spec.source_path, low_memory=False)
            self._frames[role] = frame

        required = {
            "player_id",
            "player_name",
            "season",
            "team",
            "age",
            spec.opportunity_column,
            *(metric.column for metric in spec.metrics),
        }
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"{role} 성장 분석 데이터에 필수 컬럼이 없습니다: {missing}")
        return frame.copy(), spec

    @staticmethod
    def _select_metrics(
        spec: GrowthRoleSpec, requested: Sequence[str] | None
    ) -> tuple[GrowthMetricSpec, ...]:
        metric_map = {metric.column: metric for metric in spec.metrics}
        if requested is None:
            return spec.metrics
        unknown = sorted(set(requested).difference(metric_map))
        if unknown:
            raise ValueError(f"성장 분석을 지원하지 않는 지표입니다: {unknown}")
        if not requested:
            raise ValueError("성장 분석 지표를 하나 이상 선택해야 합니다.")
        # 요청 순서를 보존하면서 중복 계산을 막는다.
        return tuple(metric_map[column] for column in dict.fromkeys(requested))

    def _population_changes(
        self, frame: pd.DataFrame, spec: GrowthRoleSpec, metric: GrowthMetricSpec
    ) -> np.ndarray:
        cache_key = (spec.role, metric.column)
        if cache_key in self._change_distributions:
            return self._change_distributions[cache_key]

        ordered = frame.sort_values(["player_id", "season"]).copy()
        grouped = ordered.groupby("player_id", sort=False)
        previous_value = grouped[metric.column].shift(1)
        previous_season = grouped["season"].shift(1)
        previous_opportunity = grouped[spec.opportunity_column].shift(1)
        direction = 1.0 if metric.higher_is_better else -1.0
        valid = (
            ordered["season"].sub(previous_season).eq(1)
            & ordered[spec.opportunity_column].ge(spec.minimum_opportunity)
            & previous_opportunity.ge(spec.minimum_opportunity)
            & ordered[metric.column].notna()
            & previous_value.notna()
        )
        changes = (
            (ordered.loc[valid, metric.column] - previous_value.loc[valid]) * direction
        ).to_numpy(dtype=float)
        if changes.size == 0:
            raise ValueError(f"변화 분포를 계산할 유효 표본이 없습니다: {metric.column}")
        changes.sort()
        self._change_distributions[cache_key] = changes
        return changes

    @staticmethod
    def _percentile(value: float, distribution: np.ndarray) -> float:
        """동점이 많은 정수 기록도 과대평가하지 않도록 mid-rank를 사용한다."""

        left = int(np.searchsorted(distribution, value, side="left"))
        right = int(np.searchsorted(distribution, value, side="right"))
        return (left + right) / (2.0 * len(distribution))

    def analyze(
        self,
        role: str,
        player_id: int,
        metrics: Sequence[str] | None = None,
    ) -> GrowthAnalysisResult:
        """선수의 전체 커리어를 long-format 성장곡선과 이벤트로 변환한다."""

        frame, spec = self._load(role)
        selected_metrics = self._select_metrics(spec, metrics)
        career = frame.loc[frame["player_id"] == player_id].sort_values("season").copy()
        if career.empty:
            raise ValueError(f"선수를 찾을 수 없습니다: {player_id}")

        curve_parts = [
            self._metric_curve(frame, career, spec, metric) for metric in selected_metrics
        ]
        curves = pd.concat(curve_parts, ignore_index=True)
        events = curves.loc[curves["event"].isin(["breakout", "decline"])].copy()
        summary = self._summarize(curves, selected_metrics)
        latest = career.iloc[-1]
        return GrowthAnalysisResult(
            player={
                "player_id": int(latest["player_id"]),
                "player_name": str(latest["player_name"]),
                "latest_team": str(latest["team"]),
                "season_min": int(career["season"].min()),
                "season_max": int(career["season"].max()),
                "season_count": int(career["season"].nunique()),
            },
            curves=curves,
            events=events.reset_index(drop=True),
            summary=summary,
        )

    def league_change_thresholds(
        self, role: str, metrics: Sequence[str] | None = None
    ) -> pd.DataFrame:
        """이벤트 판정에 사용한 리그 분포의 10·90 분위 임계값을 공개한다."""

        frame, spec = self._load(role)
        selected_metrics = self._select_metrics(spec, metrics)
        rows = []
        for metric in selected_metrics:
            distribution = self._population_changes(frame, spec, metric)
            rows.append(
                {
                    "metric": metric.column,
                    "metric_label": metric.label,
                    "sample_count": len(distribution),
                    "decline_threshold": float(np.quantile(distribution, DECLINE_PERCENTILE)),
                    "breakout_threshold": float(np.quantile(distribution, BREAKOUT_PERCENTILE)),
                }
            )
        return pd.DataFrame(rows)

    def _metric_curve(
        self,
        population: pd.DataFrame,
        career: pd.DataFrame,
        spec: GrowthRoleSpec,
        metric: GrowthMetricSpec,
    ) -> pd.DataFrame:
        distribution = self._population_changes(population, spec, metric)
        direction = 1.0 if metric.higher_is_better else -1.0
        rows: list[dict[str, object]] = []
        previous: pd.Series | None = None

        for _, season_row in career.iterrows():
            value = pd.to_numeric(season_row[metric.column], errors="coerce")
            row: dict[str, object] = {
                "season": int(season_row["season"]),
                "age": None if pd.isna(season_row["age"]) else int(season_row["age"]),
                "team": str(season_row["team"]),
                "metric": metric.column,
                "metric_label": metric.label,
                "value": None if pd.isna(value) else float(value),
                "is_qualified_season": bool(
                    pd.notna(season_row[spec.opportunity_column])
                    and season_row[spec.opportunity_column] >= spec.minimum_opportunity
                ),
                "absolute_change": None,
                "growth_rate_pct": None,
                "performance_change": None,
                "performance_growth_rate_pct": None,
                "change_percentile": None,
                "event": "not_evaluated",
                "evaluation_status": "first_season",
            }
            if previous is not None:
                row.update(
                    self._evaluate_change(
                        previous,
                        season_row,
                        value,
                        spec,
                        metric,
                        direction,
                        distribution,
                    )
                )
            rows.append(row)
            previous = season_row
        return pd.DataFrame(rows)

    def _evaluate_change(
        self,
        previous: pd.Series,
        current: pd.Series,
        current_value: float,
        spec: GrowthRoleSpec,
        metric: GrowthMetricSpec,
        direction: float,
        distribution: np.ndarray,
    ) -> dict[str, object]:
        if int(current["season"]) - int(previous["season"]) != 1:
            return {"evaluation_status": "non_consecutive_season"}

        previous_value = pd.to_numeric(previous[metric.column], errors="coerce")
        if pd.isna(current_value) or pd.isna(previous_value):
            return {"evaluation_status": "missing_value"}
        current_opportunity = pd.to_numeric(current[spec.opportunity_column], errors="coerce")
        previous_opportunity = pd.to_numeric(previous[spec.opportunity_column], errors="coerce")
        if pd.isna(current_opportunity) or pd.isna(previous_opportunity):
            return {"evaluation_status": "missing_opportunity"}
        if current_opportunity < spec.minimum_opportunity or previous_opportunity < (
            spec.minimum_opportunity
        ):
            return {"evaluation_status": "insufficient_sample"}

        absolute_change = float(current_value) - float(previous_value)
        growth_rate = (
            None
            if float(previous_value) == 0.0
            else absolute_change / abs(float(previous_value)) * 100.0
        )
        performance_change = absolute_change * direction
        percentile = self._percentile(performance_change, distribution)
        if percentile >= BREAKOUT_PERCENTILE:
            event = "breakout"
        elif percentile <= DECLINE_PERCENTILE:
            event = "decline"
        else:
            event = "stable"
        return {
            "absolute_change": absolute_change,
            "growth_rate_pct": growth_rate,
            "performance_change": performance_change,
            "performance_growth_rate_pct": (
                None if growth_rate is None else growth_rate * direction
            ),
            "change_percentile": percentile,
            "event": event,
            "evaluation_status": "evaluated",
        }

    @staticmethod
    def _summarize(curves: pd.DataFrame, metrics: tuple[GrowthMetricSpec, ...]) -> pd.DataFrame:
        summaries: list[dict[str, object]] = []
        for metric in metrics:
            metric_curve = curves.loc[curves["metric"] == metric.column]
            valid_values = metric_curve.loc[metric_curve["is_qualified_season"]].dropna(
                subset=["value"]
            )
            if valid_values.empty:
                continue
            best_index = (
                valid_values["value"].idxmax()
                if metric.higher_is_better
                else valid_values["value"].idxmin()
            )
            best = valid_values.loc[best_index]
            evaluated = metric_curve.loc[metric_curve["evaluation_status"] == "evaluated"]
            summaries.append(
                {
                    "metric": metric.column,
                    "metric_label": metric.label,
                    "latest_value": float(valid_values.iloc[-1]["value"]),
                    "best_season": int(best["season"]),
                    "best_value": float(best["value"]),
                    "average_performance_change": (
                        None if evaluated.empty else float(evaluated["performance_change"].mean())
                    ),
                    "breakout_seasons": evaluated.loc[evaluated["event"] == "breakout", "season"]
                    .astype(int)
                    .tolist(),
                    "decline_seasons": evaluated.loc[evaluated["event"] == "decline", "season"]
                    .astype(int)
                    .tolist(),
                }
            )
        return pd.DataFrame(summaries)
