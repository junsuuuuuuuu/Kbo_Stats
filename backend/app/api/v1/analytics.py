"""예측, 추천, 성장, 전성기와 가치 랭킹 REST API."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import AnalyticsServiceDependency
from app.core.constants import CURRENT_SEASON, FIRST_KBO_SEASON, LAST_COMPLETE_SEASON
from app.schemas.analytics import (
    AnalyticsRole,
    DiscoveryResponse,
    GrowthResponse,
    PeakResponse,
    PredictionResponse,
    RankingResponse,
    RankingValueType,
    SimilarPlayersResponse,
)
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/analytics", tags=["AI Analytics"])
analytics_error = {404: {"model": ErrorResponse, "description": "분석 가능한 기록이 없음"}}


@router.get(
    "/predictions/{role}/{player_id}",
    response_model=PredictionResponse,
    responses=analytics_error,
    summary="다음 시즌 성적 예측",
)
def predict_next_season(
    service: AnalyticsServiceDependency,
    role: AnalyticsRole,
    player_id: Annotated[int, Path(gt=0)],
    base_season: Annotated[
        int,
        Query(
            ge=LAST_COMPLETE_SEASON,
            le=LAST_COMPLETE_SEASON,
            description="현재 배포 모델의 학습 cutoff 시즌",
        ),
    ] = LAST_COMPLETE_SEASON,
) -> dict:
    return service.predict_next_season(role.value, player_id, base_season)


@router.get(
    "/similar/{role}/{player_id}",
    response_model=SimilarPlayersResponse,
    responses=analytics_error,
    summary="유사 선수 추천",
)
def similar_players(
    service: AnalyticsServiceDependency,
    role: AnalyticsRole,
    player_id: Annotated[int, Path(gt=0)],
    season: Annotated[
        int | None, Query(ge=FIRST_KBO_SEASON, le=LAST_COMPLETE_SEASON)
    ] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
    same_position: bool = False,
) -> dict:
    return service.similar_players(role.value, player_id, season, limit, same_position)


@router.get(
    "/discover",
    response_model=DiscoveryResponse,
    responses=analytics_error,
    summary="선수 조건 검색",
)
def discover_players(
    service: AnalyticsServiceDependency,
    role: AnalyticsRole,
    season: Annotated[
        int, Query(ge=FIRST_KBO_SEASON, le=LAST_COMPLETE_SEASON)
    ] = LAST_COMPLETE_SEASON,
    team: Annotated[str | None, Query(max_length=30)] = None,
    max_age: Annotated[float | None, Query(ge=15, le=60)] = None,
    min_ops: Annotated[float | None, Query(ge=0, le=3)] = None,
    min_obp: Annotated[float | None, Query(ge=0, le=1)] = None,
    min_slg: Annotated[float | None, Query(ge=0, le=2)] = None,
    min_home_runs: Annotated[float | None, Query(ge=0)] = None,
    max_era: Annotated[float | None, Query(ge=0, le=30)] = None,
    min_strikeouts: Annotated[float | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> dict:
    filters: dict[str, tuple[float | None, float | None]] = {"age": (None, max_age)}
    if role == AnalyticsRole.BATTING:
        filters.update(
            {
                "on_base_plus_slugging": (min_ops, None),
                "on_base_percentage": (min_obp, None),
                "slugging_percentage": (min_slg, None),
                "home_runs": (min_home_runs, None),
            }
        )
    else:
        filters.update(
            {
                "earned_run_average": (None, max_era),
                "strikeouts": (min_strikeouts, None),
            }
        )
    return service.discover(role.value, season, filters, team, limit)


@router.get(
    "/growth/{role}/{player_id}",
    response_model=GrowthResponse,
    responses=analytics_error,
    summary="선수 성장곡선 분석",
)
def growth_curve(
    service: AnalyticsServiceDependency,
    role: AnalyticsRole,
    player_id: Annotated[int, Path(gt=0)],
    metrics: Annotated[
        str | None,
        Query(max_length=200, description="쉼표로 구분한 지표 컬럼"),
    ] = None,
) -> dict:
    selected = [item.strip() for item in metrics.split(",") if item.strip()] if metrics else None
    return service.growth(role.value, player_id, selected)


@router.get(
    "/peak/{role}/{player_id}",
    response_model=PeakResponse,
    responses=analytics_error,
    summary="선수 전성기 예측",
)
def peak_prediction(
    service: AnalyticsServiceDependency,
    role: AnalyticsRole,
    player_id: Annotated[int, Path(gt=0)],
) -> dict:
    return service.peak(role.value, player_id)


@router.get(
    "/rankings",
    response_model=RankingResponse,
    responses=analytics_error,
    summary="AI 선수 가치 랭킹",
)
def value_rankings(
    service: AnalyticsServiceDependency,
    role: AnalyticsRole,
    season: Annotated[int, Query(ge=FIRST_KBO_SEASON, le=CURRENT_SEASON)] = (
        LAST_COMPLETE_SEASON
    ),
    team: Annotated[str | None, Query(max_length=30)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    value_type: RankingValueType = RankingValueType.OVERALL,
) -> dict:
    return service.rankings(role.value, season, team, limit, value_type.value)
