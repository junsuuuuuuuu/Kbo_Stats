from app.services.kbo_team_schedule import GameHitter, GamePitcher, GameTeamBox, TeamGameDetail
from app.services.recent_boxscore import aggregate_boxscores, innings_to_outs


def _detail() -> TeamGameDetail:
    hitter = GameHitter(
        batting_order="1",
        position="CF",
        player_name="A",
        at_bats=10,
        hits=4,
        runs_batted_in=2,
        runs=1,
        batting_average=0.4,
        plate_appearances=[],
        walks=2,
        hit_by_pitch=1,
        sacrifice_flies=1,
        total_bases=7,
    )
    pitcher = GamePitcher(
        player_name="P",
        appearance="선발",
        result="승",
        wins=1,
        losses=0,
        saves=0,
        innings_pitched="6.1",
        batters_faced=24,
        pitches=90,
        at_bats=20,
        hits_allowed=5,
        home_runs_allowed=0,
        walks_and_hit_batters=3,
        strikeouts=6,
        runs_allowed=2,
        earned_runs=2,
        earned_run_average=3.0,
    )
    away = GameTeamBox("SS", "삼성", "W", 5, 4, 0, 2, [], [hitter], [pitcher])
    home = GameTeamBox("LG", "LG", "L", 2, 5, 0, 1, [], [], [])
    return TeamGameDetail("20260725SSLG0", "2026-07-25", "구장", "", "", "", "", away, home, [], "")


def test_official_baseball_formulas_are_used_for_recent_boxscore_metrics():
    metrics = aggregate_boxscores([_detail()], "SS", expected_games=2)

    assert innings_to_outs("6.1") == 19
    assert innings_to_outs("1/3") == 1
    assert innings_to_outs("1 1/3") == 4
    assert metrics.batting_average == 0.4
    assert metrics.ops == 1.2
    assert metrics.boxscore_games == 1
    assert metrics.expected_games == 2
    assert metrics.ops_status == "partial"
    assert metrics.era == 54 / 19
    assert metrics.whip == 24 / 19
    assert metrics.strikeouts_per_game == 6
