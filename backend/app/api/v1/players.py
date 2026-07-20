"""선수 검색, 상세 및 시즌 기록 REST API."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import PlayerServiceDependency
from app.schemas.common import ErrorResponse
from app.schemas.player import (
    BattingSeasonResponse,
    PitchingSeasonResponse,
    PlayerDetailResponse,
    PlayerPageResponse,
    PlayerRole,
    PlayerSeasonsResponse,
    PlayerSummaryResponse,
)

router = APIRouter(prefix="/players", tags=["Players"])
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
        batting=[BattingSeasonResponse.from_entity(stat, birth_date) for stat in result.batting],
        pitching=[PitchingSeasonResponse.from_entity(stat, birth_date) for stat in result.pitching],
    )
