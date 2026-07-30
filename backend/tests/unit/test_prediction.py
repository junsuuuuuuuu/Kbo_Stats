from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.exceptions import PredictionGameNotFoundError
from app.models.standing import TeamStanding
from app.services.kbo_team_schedule import (
    GameDayTeam,
    LatestGameDay,
    LatestGameSummary,
    TeamGameResult,
)
from app.services.prediction import (
    GamePredictionService,
    _metrics,
    _pitcher_opponent_analysis,
    _pitcher_season_analysis,
    _probability,
    _recent_results,
    _record_from_results,
    _TeamInputs,
)


def _standing(code: str, wins: int, losses: int, *, home: str = "10-0-5", away: str = "8-0-7"):
    return TeamStanding(
        standing_id=1,
        season=2026,
        as_of_date=date(2026, 7, 25),
        team_id=1,
        team_code=code,
        ranking=1,
        games=wins + losses,
        wins=wins,
        losses=losses,
        draws=0,
        winning_percentage=Decimal(str(wins / (wins + losses))),
        games_behind=Decimal("0"),
        recent_ten="6-0-4",
        streak="2W",
        home_record=home,
        away_record=away,
        source_url="https://example.test/standing",
    )


def _result(team: str, opponent: str, result: str, score: int, against: int) -> TeamGameResult:
    return TeamGameResult(
        game_date="2026-07-25",
        opponent=opponent,
        venue="home",
        result=result,
        team_score=score,
        opponent_score=against,
        stadium="잠실",
        game_url=None,
        game_id=None,
    )


def _dated_result(day: str, result: str, score: int, against: int) -> TeamGameResult:
    return TeamGameResult(
        game_date=day,
        opponent="상대",
        venue="home",
        result=result,
        team_score=score,
        opponent_score=against,
        stadium="구장",
        game_url=None,
        game_id=None,
    )


def test_recent_metrics_use_only_the_latest_ten_completed_games_before_target_date():
    results = [
        _dated_result(f"2026-07-{day:02d}", "W", 10, 1)
        for day in range(1, 13)
    ]
    results.extend(
        [
            _dated_result("2026-07-26", "W", 99, 0),
            _dated_result("2026-07-27", "", 88, 0),
            _dated_result("2026-07-28", "CANCELLED", 77, 0),
        ]
    )

    recent = _recent_results(results, date(2026, 7, 26))

    assert len(recent) == 10
    assert all(item.game_date < "2026-07-26" for item in recent)
    assert all(item.result == "W" for item in recent)
    metrics = _metrics(None, recent)
    assert metrics.recent_games_count == 10
    assert metrics.recent_runs_for_per_game == 10
    assert metrics.recent_runs_against_per_game == 1
    assert metrics.recent_run_differential == 9


def test_recent_metrics_mark_partial_data_and_keep_boxscore_metrics_unavailable():
    recent = [
        _dated_result("2026-07-24", "W", 6, 3),
        _dated_result("2026-07-23", "L", 2, 4),
    ]

    metrics = _metrics(None, recent)

    assert metrics.recent_games_count == 2
    assert metrics.recent_games_status == "partial"
    assert metrics.recent_win_percentage == pytest.approx(0.5)
    assert metrics.recent_batting_average is None
    assert metrics.recent_ops is None
    assert metrics.recent_era is None
    assert metrics.recent_whip is None
    assert metrics.batting_status == "unavailable"
    assert metrics.pitching_status == "unavailable"


def test_recent_form_is_used_as_a_prediction_signal():
    strong_recent = [_dated_result("2026-07-25", "W", 8, 1)]
    weak_recent = [_dated_result("2026-07-25", "L", 1, 8)]
    away = _TeamInputs(None, strong_recent, strong_recent)
    home = _TeamInputs(None, weak_recent, weak_recent)

    probability, reasons, _ = _probability(away, home, _record_from_results([]))

    assert probability > 0.5
    assert reasons


def test_starting_pitcher_season_and_opponent_metrics_use_official_pitching_totals():
    stats = [
        SimpleNamespace(
            season=2026,
            innings_pitched_outs=30,
            earned_runs=4,
            hits_allowed=10,
            walks_allowed=3,
            strikeouts=18,
            wins=2,
            losses=1,
            games=4,
        ),
        SimpleNamespace(
            season=2025,
            innings_pitched_outs=300,
            earned_runs=100,
            hits_allowed=100,
            walks_allowed=50,
            strikeouts=100,
            wins=10,
            losses=5,
            games=20,
        ),
    ]
    appearance = SimpleNamespace(
        game_date="2026-07-25",
        opponent="LG",
        appearance_type="선발",
        result="승",
        innings_pitched="6.0",
        earned_runs=1,
        hits_allowed=4,
        walks_allowed=1,
        hit_batters=0,
        strikeouts=7,
    )

    season = _pitcher_season_analysis(stats, [appearance], 2026, date(2026, 7, 26))
    opponent = _pitcher_opponent_analysis([appearance], "LG", date(2026, 7, 26))

    assert season.games == 4
    assert season.era == pytest.approx(3.6)
    assert season.whip == pytest.approx(1.3)
    assert season.strikeouts == 18
    assert opponent.games == 1
    assert opponent.starts == 1
    assert opponent.era == pytest.approx(1.5)
    assert opponent.strikeouts == 7


def test_prediction_service_uses_player_repository_for_starting_pitcher_season_stats(
    monkeypatch: pytest.MonkeyPatch,
):
    player = SimpleNamespace(player_id=7, player_name="선발투수")
    season_stat = SimpleNamespace(
        season=2026,
        innings_pitched_outs=30,
        earned_runs=4,
        hits_allowed=10,
        walks_allowed=3,
        strikeouts=18,
        wins=2,
        losses=1,
        games=4,
    )

    class FakePlayerRepository:
        def find_pitcher(self, player_name: str, team_code: str, season: int):
            return player

        def list_pitching_seasons(self, player_id: int):
            return [season_stat]

    monkeypatch.setattr(
        "app.services.prediction.kbo_game_log_client.pitching_appearances",
        lambda player_id, season: [],
    )
    service = GamePredictionService(
        FakePredictionRepository({}),
        FakePredictionClient(_service()._client.game, {}),
        FakePlayerRepository(),
    )

    result = service._starting_pitcher(
        "선발투수", "SS", "LG", 2026, date(2026, 7, 26)
    )

    assert result.status == "available"
    assert result.season is not None
    assert result.season.era == pytest.approx(3.6)


class FakePredictionRepository:
    def __init__(self, standings: dict[str, TeamStanding | None]):
        self.standings = standings

    def get_latest_standing(self, team_code: str, season: int):
        return self.standings.get(team_code)


class FakePredictionClient:
    def __init__(self, game: LatestGameSummary, results: dict[str, list[TeamGameResult]]):
        self.game = game
        self.results_by_team = results

    def game_day(self, target_date: str, season: int):
        return LatestGameDay(target_date, [self.game], "https://example.test/schedule")

    def results(self, team_code: str, season: int):
        return self.results_by_team.get(team_code, [])


def _service(*, starters: tuple[str | None, str | None] = ("선발A", "선발B")):
    game = LatestGameSummary(
        game_id="20260726SSOB0",
        stadium="잠실",
        start_time="18:30",
        status="scheduled",
        detail_status="pending",
        detail_error=None,
        away=GameDayTeam("SS", "삼성", None, None, None, None),
        home=GameDayTeam("OB", "두산", None, None, None, None),
        away_hitter=None,
        away_pitcher=None,
        home_hitter=None,
        home_pitcher=None,
        winning_pitcher=None,
        losing_pitcher=None,
        cancellation_reason=None,
        away_starting_pitcher=starters[0],
        home_starting_pitcher=starters[1],
    )
    results = {
        "SS": [_result("삼성", "두산", "W", 6, 3), _result("삼성", "LG", "L", 2, 4)],
        "OB": [_result("두산", "삼성", "L", 3, 6), _result("두산", "LG", "W", 5, 2)],
    }
    return GamePredictionService(
        FakePredictionRepository({"SS": _standing("SS", 60, 40), "OB": _standing("OB", 50, 50)}),
        FakePredictionClient(game, results),
    )


def test_prediction_response_contains_reasons_and_probabilities_sum_to_one():
    response = _service().predict("20260726SSOB0", 2026)

    assert response.game_id == "20260726SSOB0"
    assert response.away_win_probability + response.home_win_probability == pytest.approx(1)
    assert response.key_reasons
    assert response.expected_score.away is not None


def test_prediction_handles_unknown_starting_pitcher():
    response = _service(starters=(None, "선발B")).predict("20260726SSOB0", 2026)

    assert response.away_starting_pitcher.status == "unavailable"
    assert response.confidence in {"low", "medium", "high"}


def test_prediction_handles_missing_records_without_failing():
    service = _service()
    service._repository.standings = {"SS": None, "OB": None}
    service._client.results_by_team = {"SS": [], "OB": []}

    response = service.predict("20260726SSOB0", 2026)

    assert response.away_win_probability == pytest.approx(0.5)
    assert response.home_win_probability == pytest.approx(0.5)
    assert response.confidence == "low"
    assert response.expected_score.away is None


def test_prediction_raises_for_unknown_game_id():
    with pytest.raises(PredictionGameNotFoundError):
        _service().predict("20260726XXXX0", 2026)


def test_prediction_marks_unavailable_pitcher_metrics_explicitly():
    response = _service().predict("20260726SSOB0", 2026)

    assert response.away_starting_pitcher.name == "선발A"
    assert response.away_starting_pitcher.status == "available"
    assert response.explanation
