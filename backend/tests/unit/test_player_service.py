"""PlayerService 유스케이스 단위 테스트."""

from types import SimpleNamespace

import pytest

from app.core.exceptions import PlayerNotFoundError
from app.repositories.player import calculate_defensive_efficiency
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


def test_player_seasons_include_team_defensive_efficiency() -> None:
    repository = FakePlayerRepository()
    repository.batting_stats = [SimpleNamespace(season=2026, team_id=1)]
    repository.defensive_efficiencies = {(2026, 1): 0.691}

    result = PlayerService(repository).get_player_seasons(68050, PlayerRole.BATTING)

    assert result.defensive_efficiencies == {(2026, 1): 0.691}


def test_player_seasons_load_league_rows_for_all_seasons_once() -> None:
    repository = FakePlayerRepository()
    repository.batting_stats = [
        SimpleNamespace(season=2025, team_id=1),
        SimpleNamespace(season=2026, team_id=1),
    ]

    PlayerService(repository).get_player_seasons(68050, PlayerRole.BATTING)

    assert repository.last_league_seasons == {2025, 2026}


def test_league_benchmark_calculates_average_and_percentile() -> None:
    repository = FakePlayerRepository()
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

    results = PlayerService(repository).get_league_benchmarks(68050, PlayerRole.BATTING, 2026)

    assert len(results) == 4
    assert results[0].league_average == pytest.approx(0.2675)
    assert results[0].percentile == 87.5
    assert results[0].sample_size == 4


def test_defensive_efficiency_uses_team_balls_in_play_formula() -> None:
    result = calculate_defensive_efficiency(
        batters_faced=100,
        hits_allowed=20,
        home_runs_allowed=5,
        walks_allowed=10,
        hit_batters=2,
        strikeouts=25,
        errors=3,
    )

    assert result == pytest.approx(40 / 58)
