"""PlayerService 유스케이스 단위 테스트."""

import pytest

from app.core.exceptions import PlayerNotFoundError
from app.schemas.player import PlayerRole
from app.services.player import PlayerService
from tests.fakes import FakePlayerRepository


def test_search_normalizes_name_and_pagination() -> None:
    """검색용 이름과 offset은 Router가 아니라 Service가 책임진다."""

    repository = FakePlayerRepository()
    service = PlayerService(repository)

    result = service.search_players(
        query=" 김 도 영 ",
        role=PlayerRole.BATTING,
        season=2024,
        team=" KIA ",
        page=3,
        page_size=10,
    )

    assert result.total == 1
    assert repository.last_criteria is not None
    assert repository.last_criteria.query == "김도영"
    assert repository.last_criteria.team == "KIA"
    assert repository.last_criteria.offset == 20


def test_missing_player_raises_domain_error() -> None:
    repository = FakePlayerRepository()
    repository.player = None

    with pytest.raises(PlayerNotFoundError):
        PlayerService(repository).get_player(99999)


def test_role_filter_skips_unrequested_repository_query() -> None:
    repository = FakePlayerRepository()

    result = PlayerService(repository).get_player_seasons(68050, PlayerRole.BATTING)

    assert result.pitching == []
    assert repository.batting_calls == 1
    assert repository.pitching_calls == 0
