"""구단 목록과 1군 등록 로스터 REST API."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import TeamServiceDependency
from app.schemas.common import ErrorResponse
from app.schemas.team import (
    TeamListResponse,
    TeamRosterResponse,
    TeamStandingResponse,
    TeamSummaryResponse,
)

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=TeamListResponse, summary="구단 목록 조회")
def list_teams(
    service: TeamServiceDependency,
    season: Annotated[int, Query(ge=1982, le=2200)] = 2026,
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
    season: Annotated[int, Query(ge=1982, le=2200)] = 2026,
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
    season: Annotated[int, Query(ge=1982, le=2200)] = 2026,
) -> TeamStandingResponse | None:
    standing = service.get_standing(team_code, season)
    return TeamStandingResponse.from_entity(standing) if standing is not None else None
