"""구단 목록과 1군 등록 로스터 REST API."""

from datetime import date
from typing import Annotated

import httpx
from fastapi import APIRouter, Path, Query

from app.api.dependencies import TeamServiceDependency
from app.core.constants import CURRENT_SEASON, FIRST_KBO_SEASON
from app.core.exceptions import UpstreamDataError
from app.schemas.common import ErrorResponse
from app.schemas.team import (
    LatestGameDayResponse,
    TeamGameDetailResponse,
    TeamGameResultResponse,
    TeamGameResultsResponse,
    TeamListResponse,
    TeamRosterResponse,
    TeamStandingResponse,
    TeamSummaryResponse,
)
from app.services.kbo_game_log import KBO_BASE_URL
from app.services.kbo_team_schedule import SCHEDULE_PATH, kbo_team_schedule_client

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=TeamListResponse, summary="구단 목록 조회")
def list_teams(
    service: TeamServiceDependency,
    season: Annotated[int, Query(ge=FIRST_KBO_SEASON, le=2200)] = CURRENT_SEASON,
) -> TeamListResponse:
    results = service.list_teams(season)
    return TeamListResponse(
        season=season,
        items=[TeamSummaryResponse.from_result(result) for result in results],
    )


@router.get(
    "/{team_code}/roster",
    response_model=TeamRosterResponse,
    responses={404: {"model": ErrorResponse, "description": "구단 로스터 없음"}},
    summary="구단 1군 등록 로스터 조회",
)
def get_team_roster(
    service: TeamServiceDependency,
    team_code: Annotated[str, Path(min_length=2, max_length=2)],
    season: Annotated[int, Query(ge=FIRST_KBO_SEASON, le=2200)] = CURRENT_SEASON,
) -> TeamRosterResponse:
    return TeamRosterResponse.from_result(service.get_roster(team_code, season))


@router.get(
    "/{team_code}/standing",
    response_model=TeamStandingResponse | None,
    summary="구단 최신 시즌 전적 조회",
)
def get_team_standing(
    service: TeamServiceDependency,
    team_code: Annotated[str, Path(min_length=2, max_length=2)],
    season: Annotated[int, Query(ge=FIRST_KBO_SEASON, le=2200)] = CURRENT_SEASON,
) -> TeamStandingResponse | None:
    standing = service.get_standing(team_code, season)
    return TeamStandingResponse.from_entity(standing) if standing is not None else None


@router.get(
    "/games/latest",
    response_model=LatestGameDayResponse,
    summary="가장 최근 경기일의 전체 경기와 대표 선수 조회",
)
def get_latest_games(
    service: TeamServiceDependency,
    season: Annotated[int, Query(ge=CURRENT_SEASON, le=CURRENT_SEASON)] = CURRENT_SEASON,
) -> LatestGameDayResponse:
    return LatestGameDayResponse.model_validate(service.get_latest_game_day(season).payload)


@router.get(
    "/games/day",
    response_model=LatestGameDayResponse,
    summary="선택한 날짜의 전체 경기 또는 일정 조회",
)
def get_games_by_day(
    service: TeamServiceDependency,
    game_date: Annotated[date, Query()],
    season: Annotated[int, Query(ge=CURRENT_SEASON, le=CURRENT_SEASON)] = CURRENT_SEASON,
) -> LatestGameDayResponse:
    return LatestGameDayResponse.model_validate(service.get_game_day(game_date, season).payload)


@router.get(
    "/{team_code}/games",
    response_model=TeamGameResultsResponse,
    summary="구단 시즌 경기별 승패 조회",
)
def get_team_games(
    service: TeamServiceDependency,
    team_code: Annotated[str, Path(min_length=2, max_length=2)],
    season: Annotated[int, Query(ge=CURRENT_SEASON, le=CURRENT_SEASON)] = CURRENT_SEASON,
) -> TeamGameResultsResponse:
    normalized = team_code.strip().upper()
    service.get_roster(normalized, season)
    try:
        games = kbo_team_schedule_client.results(normalized, season)
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exception:
        raise UpstreamDataError() from exception
    return TeamGameResultsResponse(
        season=season,
        team_code=normalized,
        source_url=f"{KBO_BASE_URL}{SCHEDULE_PATH}",
        items=[TeamGameResultResponse.model_validate(game, from_attributes=True) for game in games],
    )


@router.get(
    "/{team_code}/games/{game_id}",
    response_model=TeamGameDetailResponse,
    summary="구단 경기 박스스코어 조회",
)
def get_team_game_detail(
    service: TeamServiceDependency,
    team_code: Annotated[str, Path(min_length=2, max_length=2)],
    game_id: Annotated[str, Path(min_length=13, max_length=16)],
    season: Annotated[int, Query(ge=CURRENT_SEASON, le=CURRENT_SEASON)] = CURRENT_SEASON,
) -> TeamGameDetailResponse:
    normalized = team_code.strip().upper()
    service.get_roster(normalized, season)
    try:
        detail = kbo_team_schedule_client.game_detail(game_id.upper(), season)
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exception:
        raise UpstreamDataError() from exception
    if normalized not in {detail.away.team_code, detail.home.team_code}:
        raise UpstreamDataError()
    return TeamGameDetailResponse.model_validate(detail, from_attributes=True)
