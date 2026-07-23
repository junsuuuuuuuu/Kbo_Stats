"""선수 REST API 계약 테스트."""

from types import SimpleNamespace

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
    assert "/api/v1/players/{player_id}/overview" in paths
    assert "/api/v1/players/{player_id}/benchmarks" in paths
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


async def test_player_overview_combines_profile_and_seasons(client: AsyncClient) -> None:
    response = await client.get("/api/v1/players/68050/overview")

    assert response.status_code == 200
    assert response.json()["player"]["player_name"] == "김도영"
    assert response.json()["seasons"] == {
        "player_id": 68050,
        "batting": [],
        "pitching": [],
    }


async def test_player_benchmark_contract(
    client: AsyncClient, repository: FakePlayerRepository
) -> None:
    repository.batting_stats = [
        SimpleNamespace(
            season=2026,
            batting_average=0.320,
            on_base_plus_slugging=0.900,
            home_runs=20,
            runs_batted_in=70,
        )
    ]
    repository.metric_values = [0.200, 0.250, 0.300, 0.320]

    response = await client.get(
        "/api/v1/players/68050/benchmarks",
        params={"role": "BATTING", "season": 2026},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["qualification"] == "100타석 이상"
    assert body["items"][0]["metric"] == "batting_average"
    assert body["items"][0]["percentile"] == 87.5
