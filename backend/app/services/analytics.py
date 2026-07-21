"""HTTP 계층과 ML 모듈 사이의 분석 유스케이스 조립."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.core.exceptions import AnalyticsNotAvailableError
from app.ml.growth import PlayerGrowthAnalyzer
from app.ml.inference import NextSeasonPredictor
from app.ml.peak_inference import PeakPredictor
from app.ml.ranking import PlayerValueRanker
from app.ml.ranking_config import COMPONENT_LABELS
from app.ml.recommendation import NumericCondition, PlayerRecommendationEngine
from app.ml.recommendation_config import RECOMMENDATION_SPECS


def _clean_record(record: dict[str, Any]) -> dict[str, Any]:
    """Pandas/NumPy scalar와 NaN을 JSON 안전 값으로 변환한다."""

    cleaned = {}
    for key, value in record.items():
        if isinstance(value, list):
            cleaned[key] = value
        elif pd.isna(value):
            cleaned[key] = None
        elif hasattr(value, "item"):
            cleaned[key] = value.item()
        else:
            cleaned[key] = value
    return cleaned


class AnalyticsService:
    """ML 엔진을 프로세스 내에서 재사용하고 API용 dict로 변환한다."""

    def __init__(self) -> None:
        self._next_season = NextSeasonPredictor()
        self._recommendation = PlayerRecommendationEngine()
        self._growth = PlayerGrowthAnalyzer()
        self._peak = PeakPredictor()
        self._ranking = PlayerValueRanker()

    def predict_next_season(self, role: str, player_id: int, base_season: int) -> dict:
        targets = (
            ("batting_average", "on_base_plus_slugging", "home_runs")
            if role == "batting"
            else ("earned_run_average", "strikeouts")
        )
        predictions = []
        for target in targets:
            result = self._next_season.predict_season(target, base_season)
            matched = result.loc[result["player_id"] == player_id]
            if matched.empty:
                continue
            row = matched.iloc[0]
            predictions.append(
                {
                    "target": target,
                    "target_season": int(row["target_season"]),
                    "prediction": float(row["prediction"]),
                    "previous_season_value": float(row["previous_season_value"]),
                }
            )
        if not predictions:
            raise AnalyticsNotAvailableError(
                "다음 시즌 예측에 필요한 연속 3년 기록이 없습니다.",
                {"player_id": player_id, "base_season": base_season},
            )
        return {
            "player_id": player_id,
            "role": role,
            "base_season": base_season,
            "predictions": predictions,
        }

    def similar_players(
        self, role: str, player_id: int, season: int | None, limit: int, same_position: bool
    ) -> dict:
        try:
            result = self._recommendation.recommend_similar(
                role, player_id, season=season, top_k=limit, same_position=same_position
            )
        except ValueError as exception:
            raise AnalyticsNotAvailableError(
                str(exception), {"player_id": player_id}
            ) from exception
        columns = [
            "rank",
            "player_id",
            "player_name",
            "team",
            "cosine_score",
            "knn_score",
            "similarity_score",
            "reasons",
        ]
        return {
            "reference": result.reference,
            "recommendations": [
                _clean_record(item)
                for item in result.recommendations[columns].to_dict(orient="records")
            ],
            "pca_coordinates": [
                _clean_record(item) for item in result.pca_coordinates.to_dict(orient="records")
            ],
            "pca_explained_variance_ratio": list(result.pca_explained_variance_ratio),
        }

    def discover(
        self,
        role: str,
        season: int,
        filters: dict[str, tuple[float | None, float | None]],
        team: str | None,
        limit: int,
    ) -> dict:
        conditions = tuple(
            NumericCondition(column, minimum, maximum)
            for column, (minimum, maximum) in filters.items()
            if minimum is not None or maximum is not None
        )
        try:
            result = self._recommendation.search_by_conditions(
                role, conditions, season=season, team=team, limit=limit
            )
        except ValueError as exception:
            raise AnalyticsNotAvailableError(str(exception)) from exception
        identity = {"player_id", "player_name", "season", "team", "age"}
        items = []
        for record in result.to_dict(orient="records"):
            cleaned = _clean_record(record)
            items.append(
                {
                    **{key: cleaned.get(key) for key in identity},
                    "stats": {
                        key: value
                        for key, value in cleaned.items()
                        if key in RECOMMENDATION_SPECS[role].filterable_columns
                    },
                }
            )
        return {"role": role, "season": season, "items": items}

    def growth(self, role: str, player_id: int, metrics: list[str] | None) -> dict:
        try:
            result = self._growth.analyze(role, player_id, metrics)
        except ValueError as exception:
            raise AnalyticsNotAvailableError(
                str(exception), {"player_id": player_id}
            ) from exception
        curve_columns = [
            "season",
            "age",
            "team",
            "metric",
            "metric_label",
            "value",
            "absolute_change",
            "growth_rate_pct",
            "performance_change",
            "change_percentile",
            "event",
            "evaluation_status",
        ]
        return {
            "player": result.player,
            "curves": [
                _clean_record(item)
                for item in result.curves[curve_columns].to_dict(orient="records")
            ],
            "events": [
                _clean_record(item)
                for item in result.events[curve_columns].to_dict(orient="records")
            ],
            "summary": [_clean_record(item) for item in result.summary.to_dict(orient="records")],
        }

    def peak(self, role: str, player_id: int) -> dict:
        try:
            return self._peak.predict_player(role, player_id)
        except ValueError as exception:
            raise AnalyticsNotAvailableError(
                str(exception), {"player_id": player_id}
            ) from exception

    def rankings(
        self,
        role: str,
        season: int,
        team: str | None,
        limit: int,
        value_type: str = "overall",
    ) -> dict[str, Any]:
        if role == "pitching":
            value_type = "overall"
        try:
            result = self._ranking.rank_season(
                role, season=season, team=team, limit=limit, value_type=value_type
            )
        except ValueError as exception:
            raise AnalyticsNotAvailableError(str(exception)) from exception
        components = [column for column in COMPONENT_LABELS if column in result.columns]
        items = []
        for record in result.to_dict(orient="records"):
            cleaned = _clean_record(record)
            items.append(
                {
                    "season_rank": cleaned["season_rank"],
                    "team_rank": cleaned["team_rank"],
                    "player_id": cleaned["player_id"],
                    "player_name": cleaned["player_name"],
                    "team": cleaned["team"],
                    "age": cleaned["age"],
                    "ai_score": cleaned["ai_score"],
                    "components": {column: cleaned[column] for column in components},
                    "reasons": cleaned["reasons"],
                }
            )
        return {"role": role, "season": season, "value_type": value_type, "items": items}
