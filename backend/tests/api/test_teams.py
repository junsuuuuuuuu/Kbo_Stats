"""구단 목록과 1군 등록 로스터 REST API 계약 테스트."""

import pytest
from httpx import AsyncClient

from tests.fakes import FakeTeamRepository

pytestmark = pytest.mark.anyio


async def test_team_list_returns_latest_roster_summary(client: AsyncClient) -> None:
    response = await client.get("/api/v1/teams", params={"season": 2026})

    assert response.status_code == 200
    assert response.json() == {
        "season": 2026,
        "items": [
            {
                "team_id": 1,
                "team_code": "SS",
                "team_name": "삼성",
                "season": 2026,
                "as_of_date": "2026-07-20",
                "roster_count": 1,
                "pitcher_count": 1,
                "hitter_count": 0,
            }
        ],
    }


async def test_team_roster_links_member_to_player(client: AsyncClient) -> None:
    response = await client.get("/api/v1/teams/ss/roster", params={"season": 2026})

    assert response.status_code == 200
    body = response.json()
    assert body["team"]["team_code"] == "SS"
    assert body["members"][0] == {
        "player_id": 68050,
        "player_name": "김도영",
        "uniform_number": "18",
        "position": "P",
        "position_label": "투수",
        "bat_side": "R",
        "throw_side": "R",
        "birth_date": "2003-10-02",
        "age": 23,
        "height_cm": 183,
        "weight_kg": 92,
        "source_url": "https://example.test/player/68050",
    }


async def test_missing_team_roster_uses_common_error(
    client: AsyncClient, team_repository: FakeTeamRepository
) -> None:
    team_repository.snapshot = None

    response = await client.get("/api/v1/teams/XX/roster", params={"season": 2026})

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "TEAM_ROSTER_NOT_FOUND",
        "message": "구단 로스터를 찾을 수 없습니다.",
        "details": {"team_code": "XX", "season": 2026},
    }


async def test_team_standing_returns_latest_snapshot(client: AsyncClient) -> None:
    response = await client.get("/api/v1/teams/SS/standing", params={"season": 2026})

    assert response.status_code == 200
    body = response.json()
    assert body["ranking"] == 1
    assert body["wins"] == 52
    assert body["recent_ten"] == "8승0무2패"
    assert body["team_name"] == "삼성"
