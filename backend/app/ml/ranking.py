"""시즌 내 백분위 기반의 설명 가능한 AI 선수 가치 랭킹."""

from __future__ import annotations

from collections.abc import Mapping
from threading import RLock

import numpy as np
import pandas as pd

from app.ml.ranking_config import COMPONENT_LABELS, RANKING_SPECS, RankingSpec


class PlayerValueRanker:
    """역할별 세부 점수, 종합 AI Score, 시즌·팀 순위를 계산한다."""

    def __init__(self, frames: Mapping[str, pd.DataFrame] | None = None) -> None:
        self._frames = {key: value.copy() for key, value in (frames or {}).items()}
        self._ranking_cache: dict[tuple[str, int], pd.DataFrame] = {}
        self._lock = RLock()

    @staticmethod
    def _spec(role: str) -> RankingSpec:
        try:
            return RANKING_SPECS[role]
        except KeyError as exception:
            raise ValueError(f"지원하지 않는 선수 역할입니다: {role}") from exception

    def _load(self, role: str) -> tuple[pd.DataFrame, RankingSpec]:
        spec = self._spec(role)
        frame = self._frames.get(role)
        if frame is None:
            frame = pd.read_csv(spec.source_path, low_memory=False)
            self._frames[role] = frame
        return frame.copy(), spec

    @staticmethod
    def _percentile(series: pd.Series, *, higher_is_better: bool = True) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce")
        percentile = numeric.rank(method="average", pct=True)
        if not higher_is_better:
            percentile = 1.0 - percentile + (1.0 / max(numeric.notna().sum(), 1))
        return percentile.fillna(0.5).clip(0.0, 1.0)

    @staticmethod
    def _safe_rate(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
        denominator = pd.to_numeric(denominator, errors="coerce").replace(0, np.nan)
        return pd.to_numeric(numerator, errors="coerce").div(denominator)

    def _consistency(
        self, full_frame: pd.DataFrame, season_frame: pd.DataFrame, spec: RankingSpec
    ) -> pd.Series:
        target_season = int(season_frame["season"].iloc[0])
        years = [target_season - 2, target_season - 1, target_season]
        history = full_frame.loc[
            full_frame["season"].isin(years)
            & full_frame[spec.opportunity_column].ge(spec.minimum_opportunity),
            ["player_id", "season", spec.primary_metric],
        ].copy()
        history[spec.primary_metric] = pd.to_numeric(
            history[spec.primary_metric], errors="coerce"
        )
        values = history.pivot_table(
            index="player_id", columns="season", values=spec.primary_metric, aggfunc="first"
        ).reindex(columns=years)
        # 직전 시즌이 없으면 2년 전 기록을 건너뛰어 연결하지 않는다.
        values.loc[values[target_season - 1].isna(), target_season - 2] = np.nan
        consistency_std = values.std(axis=1, skipna=True, ddof=1)
        aligned = season_frame["player_id"].map(consistency_std)
        return self._percentile(aligned, higher_is_better=False)

    def _batting_components(
        self, full_frame: pd.DataFrame, frame: pd.DataFrame, spec: RankingSpec
    ) -> pd.DataFrame:
        components = pd.DataFrame(index=frame.index)
        components["offense_score"] = pd.concat(
            [
                self._percentile(frame["batting_average"]),
                self._percentile(frame["on_base_plus_slugging"]),
            ],
            axis=1,
        ).mean(axis=1)
        walk_rate = self._safe_rate(frame["walks"], frame["plate_appearances"])
        components["on_base_score"] = pd.concat(
            [self._percentile(frame["on_base_percentage"]), self._percentile(walk_rate)], axis=1
        ).mean(axis=1)
        home_run_rate = self._safe_rate(frame["home_runs"], frame["plate_appearances"])
        components["power_score"] = pd.concat(
            [self._percentile(frame["slugging_percentage"]), self._percentile(home_run_rate)],
            axis=1,
        ).mean(axis=1)
        components["speed_score"] = self._percentile(
            self._safe_rate(frame["stolen_bases"], frame["plate_appearances"])
        )
        components["consistency_score"] = self._consistency(full_frame, frame, spec).to_numpy()
        components["availability_score"] = pd.concat(
            [self._percentile(frame["games"]), self._percentile(frame["plate_appearances"])],
            axis=1,
        ).mean(axis=1)
        components["age_potential_score"] = self._percentile(frame["age"], higher_is_better=False)
        raw_contribution = frame["runs"] + frame["runs_batted_in"] + frame["home_runs"] * 0.5
        team_total = raw_contribution.groupby(frame["team"]).transform("sum").replace(0, np.nan)
        components["team_contribution_score"] = self._percentile(raw_contribution / team_total)
        return components

    def _pitching_components(
        self, full_frame: pd.DataFrame, frame: pd.DataFrame, spec: RankingSpec
    ) -> pd.DataFrame:
        components = pd.DataFrame(index=frame.index)
        components["run_prevention_score"] = self._percentile(
            frame["earned_run_average"], higher_is_better=False
        )
        components["strikeout_score"] = self._percentile(
            self._safe_rate(frame["strikeouts"], frame["batters_faced"])
        )
        components["control_score"] = self._percentile(
            self._safe_rate(frame["walks_allowed"], frame["batters_faced"]),
            higher_is_better=False,
        )
        components["leverage_score"] = pd.concat(
            [self._percentile(frame["saves"]), self._percentile(frame["holds"])], axis=1
        ).max(axis=1)
        components["consistency_score"] = self._consistency(full_frame, frame, spec).to_numpy()
        components["workload_score"] = pd.concat(
            [
                self._percentile(frame["innings_pitched_outs"]),
                self._percentile(frame["games"]),
            ],
            axis=1,
        ).mean(axis=1)
        components["age_potential_score"] = self._percentile(frame["age"], higher_is_better=False)
        raw_contribution = (
            frame["wins"] * 3 + frame["saves"] * 2 + frame["holds"] + frame["strikeouts"] * 0.1
        )
        team_total = raw_contribution.groupby(frame["team"]).transform("sum").replace(0, np.nan)
        components["team_contribution_score"] = self._percentile(raw_contribution / team_total)
        return components

    def rank_season(
        self,
        role: str,
        *,
        season: int | None = None,
        team: str | None = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """해당 시즌 전체 후보로 점수를 계산한 뒤 선택적으로 팀 결과를 반환한다."""

        full_frame, spec = self._load(role)
        target_season = int(full_frame["season"].max()) if season is None else season
        cache_key = (role, target_season)
        with self._lock:
            cached = self._ranking_cache.get(cache_key)
        if cached is not None:
            result = cached.copy()
            if team is not None:
                result = result.loc[result["team"] == team]
            if limit < 1:
                raise ValueError("랭킹 limit은 1 이상이어야 합니다.")
            return result.head(limit).reset_index(drop=True)

        frame = full_frame.loc[
            full_frame["season"].eq(target_season)
            & full_frame[spec.opportunity_column].ge(spec.minimum_opportunity)
        ].copy()
        if frame.empty:
            raise ValueError(f"랭킹을 계산할 유효 선수가 없습니다: {role}/{target_season}")

        components = (
            self._batting_components(full_frame, frame, spec)
            if role == "batting"
            else self._pitching_components(full_frame, frame, spec)
        )
        result = frame.copy()
        for column in spec.component_weights:
            result[column] = components[column] * 100.0
        result["ai_score"] = sum(
            result[column] * weight for column, weight in spec.component_weights.items()
        )
        result["season_rank"] = result["ai_score"].rank(method="min", ascending=False).astype(int)
        result["team_rank"] = (
            result.groupby("team")["ai_score"].rank(method="min", ascending=False).astype(int)
        )
        component_columns = list(spec.component_weights)
        result["reasons"] = result[component_columns].apply(self._top_reasons, axis=1)
        result = result.sort_values(["ai_score", "player_id"], ascending=[False, True])
        with self._lock:
            self._ranking_cache[cache_key] = result.copy()
        if team is not None:
            result = result.loc[result["team"] == team]
        if limit < 1:
            raise ValueError("랭킹 limit은 1 이상이어야 합니다.")
        return result.head(limit).reset_index(drop=True)

    @staticmethod
    def _top_reasons(component_scores: pd.Series) -> list[str]:
        return [
            f"{COMPONENT_LABELS[column]} 상위 {max(1, round(100 - score))}%"
            for column, score in component_scores.nlargest(3).items()
        ]
