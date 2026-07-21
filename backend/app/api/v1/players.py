"""선수 검색, 상세 및 시즌 기록 REST API."""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Path, Query

from app.api.dependencies import PlayerServiceDependency
from app.core.exceptions import UpstreamDataError
from app.schemas.common import ErrorResponse
from app.schemas.player import (
    BattingAppearanceResponse,
    BattingAppearancesResponse,
    BattingSeasonResponse,
    LeagueBenchmarkResponse,
    PitchingAppearanceResponse,
    PitchingAppearancesResponse,
    PitchingSeasonResponse,
    PlayerBenchmarksResponse,
    PlayerDetailResponse,
    PlayerPageResponse,
    PlayerRole,
    PlayerSeasonsResponse,
    PlayerSummaryResponse,
)
from app.services.kbo_game_log import (
    DAILY_PATH,
    HITTER_DAILY_PATH,
    KBO_BASE_URL,
    kbo_game_log_client,
)

router = APIRouter(prefix="/players", tags=["Players"])
logger = logging.getLogger("kbo_api")
not_found_response = {404: {"model": ErrorResponse, "description": "선수를 찾을 수 없음"}}


@router.get("", response_model=PlayerPageResponse, summary="선수 검색")
def search_players(
    service: PlayerServiceDependency,
    query: Annotated[
        str | None,
        Query(min_length=1, max_length=100, description="선수명 prefix"),
    ] = None,
    role: Annotated[PlayerRole | None, Query(description="타자 또는 투수 역할")] = None,
    season: Annotated[int | None, Query(ge=1982, le=2200)] = None,
    team: Annotated[str | None, Query(min_length=1, max_length=30)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PlayerPageResponse:
    """이름, 역할, 시즌과 팀 조건으로 선수를 페이지 조회한다."""

    result = service.search_players(
        query=query,
        role=role,
        season=season,
        team=team,
        page=page,
        page_size=page_size,
    )
    return PlayerPageResponse(
        items=[PlayerSummaryResponse.from_entity(player) for player in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.get(
    "/{player_id}",
    response_model=PlayerDetailResponse,
    responses=not_found_response,
    summary="선수 기본 정보 조회",
)
def get_player(
    service: PlayerServiceDependency,
    player_id: Annotated[int, Path(gt=0)],
) -> PlayerDetailResponse:
    """동명이인과 무관한 player_id로 선수 프로필을 조회한다."""

    return PlayerDetailResponse.from_entity(service.get_player(player_id))


@router.get(
    "/{player_id}/seasons",
    response_model=PlayerSeasonsResponse,
    responses=not_found_response,
    summary="선수 시즌 기록 조회",
)
def get_player_seasons(
    service: PlayerServiceDependency,
    player_id: Annotated[int, Path(gt=0)],
    role: Annotated[PlayerRole | None, Query(description="생략하면 두 역할 모두 조회")] = None,
) -> PlayerSeasonsResponse:
    """Plotly와 표에서 사용할 역할별 시즌 기록을 연도순으로 반환한다."""

    result = service.get_player_seasons(player_id, role)
    birth_date = result.player.birth_date
    return PlayerSeasonsResponse(
        player_id=result.player.player_id,
        batting=[
            BattingSeasonResponse.from_entity(
                stat,
                birth_date,
                result.defensive_efficiencies.get((stat.season, stat.team_id)),
                result.batting_metrics.get(id(stat)),
                result.team_rankings.get((stat.season, stat.team_id)),
            )
            for stat in result.batting
        ],
        pitching=[PitchingSeasonResponse.from_entity(stat, birth_date) for stat in result.pitching],
    )


@router.get(
    "/{player_id}/pitching-appearances",
    response_model=PitchingAppearancesResponse,
    responses=not_found_response,
    summary="투수 시즌 등판별 기록 조회",
)
def get_pitching_appearances(
    service: PlayerServiceDependency,
    player_id: Annotated[int, Path(gt=0)],
    season: Annotated[int, Query(ge=2026, le=2026)] = 2026,
) -> PitchingAppearancesResponse:
    """KBO 공식 일자별 기록에서 2026 정규시즌의 모든 등판을 반환한다."""

    service.get_player(player_id)
    try:
        items = kbo_game_log_client.pitching_appearances(player_id, season)
    except (httpx.HTTPError, UnicodeError, ValueError) as exception:
        logger.warning("kbo_game_log_failed player_id=%s error=%s", player_id, exception)
        raise UpstreamDataError() from exception
    return PitchingAppearancesResponse(
        player_id=player_id,
        season=season,
        source_url=f"{KBO_BASE_URL}{DAILY_PATH}?playerId={player_id}",
        items=[
            PitchingAppearanceResponse.model_validate(item, from_attributes=True)
            for item in items
        ],
    )


@router.get(
    "/{player_id}/batting-appearances",
    response_model=BattingAppearancesResponse,
    responses=not_found_response,
    summary="타자 시즌 경기별 기록 조회",
)
def get_batting_appearances(
    service: PlayerServiceDependency,
    player_id: Annotated[int, Path(gt=0)],
    season: Annotated[int, Query(ge=2026, le=2026)] = 2026,
) -> BattingAppearancesResponse:
    """KBO 공식 일자별 기록에서 2026 정규시즌의 모든 타자 출장을 반환한다."""

    service.get_player(player_id)
    try:
        items = kbo_game_log_client.batting_appearances(player_id, season)
    except (httpx.HTTPError, UnicodeError, ValueError) as exception:
        logger.warning("kbo_batting_log_failed player_id=%s error=%s", player_id, exception)
        raise UpstreamDataError() from exception
    return BattingAppearancesResponse(
        player_id=player_id,
        season=season,
        source_url=f"{KBO_BASE_URL}{HITTER_DAILY_PATH}?playerId={player_id}",
        items=[
            BattingAppearanceResponse.model_validate(item, from_attributes=True)
            for item in items
        ],
    )


@router.get(
    "/{player_id}/benchmarks",
    response_model=PlayerBenchmarksResponse,
    responses=not_found_response,
    summary="선수 시즌 기록의 리그 평균·백분위 조회",
)
def get_player_benchmarks(
    service: PlayerServiceDependency,
    player_id: Annotated[int, Path(gt=0)],
    role: Annotated[PlayerRole, Query()],
    season: Annotated[int, Query(ge=1982, le=2200)],
) -> PlayerBenchmarksResponse:
    items = service.get_league_benchmarks(player_id, role, season)
    qualification = "100타석 이상" if role is PlayerRole.BATTING else "30이닝 이상"
    return PlayerBenchmarksResponse(
        player_id=player_id,
        role=role.value.lower(),
        season=season,
        qualification=qualification,
        items=[
            LeagueBenchmarkResponse(
                metric=item.metric,
                player_value=item.player_value,
                league_average=item.league_average,
                percentile=item.percentile,
                sample_size=item.sample_size,
                higher_is_better=item.higher_is_better,
            )
            for item in items
        ],
    )
