from types import SimpleNamespace

import pytest

from app.analytics.batting_metrics import calculate_batting_metrics


def _line(**overrides: int):
    values = {
        "plate_appearances": 500,
        "at_bats": 440,
        "runs": 80,
        "hits": 132,
        "doubles": 25,
        "triples": 3,
        "home_runs": 20,
        "stolen_bases": 15,
        "caught_stealing": 5,
        "walks": 45,
        "hit_by_pitch": 5,
        "strikeouts": 90,
        "grounded_into_double_play": 10,
        "sacrifice_flies": 5,
        "batting_average": 0.300,
        "slugging_percentage": 0.507,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_calculates_basic_and_weighted_batting_metrics() -> None:
    player = _line()
    league = [_line(), _line(runs=60, hits=110, home_runs=10, stolen_bases=5)]

    result = calculate_batting_metrics(player, league)

    assert result.walk_percentage == pytest.approx(0.09)
    assert result.strikeout_percentage == pytest.approx(0.18)
    assert result.walk_to_strikeout_ratio == pytest.approx(0.5)
    assert result.isolated_power == pytest.approx(0.207)
    assert result.batting_average_on_balls_in_play == pytest.approx(112 / 335)
    assert result.stolen_base_percentage == pytest.approx(0.75)
    assert result.speed_score is not None and 0 <= result.speed_score <= 10
    assert result.weighted_on_base_average is not None
    assert result.weighted_runs_created_plus is not None


def test_zero_denominators_return_none_instead_of_crashing() -> None:
    empty = _line(
        plate_appearances=0, at_bats=0, runs=0, hits=0, doubles=0, triples=0,
        home_runs=0, stolen_bases=0, caught_stealing=0, walks=0, hit_by_pitch=0,
        strikeouts=0, grounded_into_double_play=0, sacrifice_flies=0,
    )

    result = calculate_batting_metrics(empty, [empty])

    assert result.walk_percentage is None
    assert result.strikeout_percentage is None
    assert result.walk_to_strikeout_ratio is None
    assert result.batting_average_on_balls_in_play is None
    assert result.stolen_base_percentage is None
    assert result.weighted_runs_created_plus is None
