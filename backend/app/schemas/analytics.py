"""ML 예측·추천·성장·랭킹 REST 응답 계약."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AnalyticsRole(StrEnum):
    BATTING = "batting"
    PITCHING = "pitching"


class RankingValueType(StrEnum):
    OVERALL = "overall"
    OFFENSE = "offense"
    DEFENSE = "defense"


class PredictionItem(BaseModel):
    target: str
    target_season: int
    prediction: float
    previous_season_value: float


class PredictionResponse(BaseModel):
    player_id: int
    role: AnalyticsRole
    base_season: int
    predictions: list[PredictionItem]


class SimilarPlayerItem(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team: str
    cosine_score: float = Field(ge=0, le=1)
    knn_score: float = Field(ge=0, le=1)
    similarity_score: float = Field(ge=0, le=1)
    reasons: list[str]


class PcaPoint(BaseModel):
    player_id: int
    player_name: str
    pca_x: float
    pca_y: float
    is_reference: bool


class SimilarPlayersResponse(BaseModel):
    reference: dict[str, Any]
    recommendations: list[SimilarPlayerItem]
    pca_coordinates: list[PcaPoint]
    pca_explained_variance_ratio: list[float]


class DiscoveryItem(BaseModel):
    player_id: int
    player_name: str
    season: int
    team: str
    age: int | None
    stats: dict[str, Any]


class DiscoveryResponse(BaseModel):
    role: AnalyticsRole
    season: int
    items: list[DiscoveryItem]


class GrowthPoint(BaseModel):
    season: int
    age: int | None
    team: str
    metric: str
    metric_label: str
    value: float | None
    absolute_change: float | None
    growth_rate_pct: float | None
    performance_change: float | None
    change_percentile: float | None
    event: str
    evaluation_status: str


class GrowthResponse(BaseModel):
    player: dict[str, Any]
    curves: list[GrowthPoint]
    events: list[GrowthPoint]
    summary: list[dict[str, Any]]


class PeakModelDetail(BaseModel):
    deployed_model: str
    candidate_model: str
    validation_mae: float | None
    baseline_mae: float | None
    uses_baseline_fallback: bool


class PeakResponse(BaseModel):
    player_id: int
    player_name: str
    role: AnalyticsRole
    current_age: float | None
    feature_cutoff_season: int
    qualified_season_count: int
    peak_timing: str
    predictions: dict[str, float]
    model_details: dict[str, PeakModelDetail]


class RankingItem(BaseModel):
    season_rank: int
    team_rank: int
    player_id: int
    player_name: str
    team: str
    age: int | None
    ai_score: float = Field(ge=0, le=100)
    components: dict[str, float]
    reasons: list[str]


class RankingResponse(BaseModel):
    role: AnalyticsRole
    season: int
    value_type: RankingValueType
    items: list[RankingItem]
