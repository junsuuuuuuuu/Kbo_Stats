"""선수 REST API 계약 테스트."""

import pytest
from httpx import AsyncClient

from tests.fakes import FakePlayerRepository

pytestmark = pytest.mark.anyio


async def test_health_returns_request_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "local"}
    assert response.headers["x-request-id"]


async def test_openapi_contains_versioned_player_routes(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/players" in paths
    assert "/api/v1/players/{player_id}/seasons" in paths
    assert "/api/v1/teams/{team_code}/roster" in paths


async def test_search_response_and_query_normalization(
    client: AsyncClient, repository: FakePlayerRepository
) -> None:
    response = await client.get(
        "/api/v1/players",
        params={"query": " 김 도영 ", "role": "BATTING", "page": 1, "page_size": 10},
    )

    assert response.status_code == 200
    assert response.json()["items"][0] == {
        "player_id": 68050,
        "player_name": "김도영",
        "birth_date": "2003-10-02",
        "roles": ["BATTING"],
    }
    assert repository.last_criteria is not None
    assert repository.last_criteria.query == "김도영"


async def test_missing_player_uses_common_error_contract(
    client: AsyncClient, repository: FakePlayerRepository
) -> None:
    repository.player = None

    response = await client.get("/api/v1/players/99999")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "PLAYER_NOT_FOUND",
            "message": "선수를 찾을 수 없습니다.",
            "details": {"player_id": 99999},
        }
    }


async def test_validation_error_uses_common_error_contract(client: AsyncClient) -> None:
    response = await client.get("/api/v1/players", params={"page_size": 101})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_role_specific_season_response_skips_other_role(
    client: AsyncClient, repository: FakePlayerRepository
) -> None:
    response = await client.get("/api/v1/players/68050/seasons", params={"role": "BATTING"})

    assert response.status_code == 200
    assert response.json() == {"player_id": 68050, "batting": [], "pitching": []}
    assert repository.batting_calls == 1
    assert repository.pitching_calls == 0
