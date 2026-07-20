"""실제 ML service를 사용하는 분석 REST API smoke test."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_ranking_api_returns_typed_top_players(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/analytics/rankings",
        params={"role": "batting", "season": 2025, "limit": 3},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "batting"
    assert len(body["items"]) == 3
    assert body["items"][0]["season_rank"] == 1
    assert 0 <= body["items"][0]["ai_score"] <= 100
    assert "max-age=60" in response.headers["cache-control"]


async def test_peak_api_loads_saved_models(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/peak/batting/71837")

    assert response.status_code == 200
    assert set(response.json()["predictions"]) == {
        "peak_age",
        "peak_ops",
        "peak_home_runs",
    }


async def test_analytics_validation_uses_common_error_contract(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/analytics/rankings", params={"role": "batting", "limit": 101}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_prediction_rejects_season_before_deployed_model_cutoff(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/analytics/predictions/batting/71837",
        params={"base_season": 2024},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
