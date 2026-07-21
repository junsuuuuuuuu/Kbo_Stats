"""Backend 테스트 공통 fixture."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_player_service, get_team_service
from app.main import create_app
from app.services.player import PlayerService
from app.services.team import TeamService
from tests.fakes import FakePlayerRepository, FakeTeamRepository


@pytest.fixture
def repository() -> FakePlayerRepository:
    """DB 연결 없이 Service 동작을 관찰할 수 있는 Repository 대역."""

    return FakePlayerRepository()


@pytest.fixture
def team_repository() -> FakeTeamRepository:
    """구단 로스터 Repository 대역."""

    return FakeTeamRepository()


@pytest.fixture
def anyio_backend() -> str:
    """CI 환경마다 결과가 달라지지 않도록 asyncio backend를 명시한다."""

    return "asyncio"


@pytest.fixture
async def client(
    repository: FakePlayerRepository,
    team_repository: FakeTeamRepository,
) -> AsyncGenerator[AsyncClient, None]:
    """실제 dependency wiring 중 Service만 테스트 대역으로 교체한다."""

    application = create_app()
    application.dependency_overrides[get_player_service] = lambda: PlayerService(repository)
    application.dependency_overrides[get_team_service] = lambda: TeamService(team_repository)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    application.dependency_overrides.clear()
