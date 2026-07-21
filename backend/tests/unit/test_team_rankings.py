from app.analytics.team_rankings import final_team_rank


def test_official_final_team_rank_is_returned_for_historical_name() -> None:
    assert final_team_rank(2018, "SK") == 1
    assert final_team_rank(2024, "SSG") == 6
    assert final_team_rank(2025, "SSG") == 3


def test_unknown_season_or_team_has_no_rank() -> None:
    assert final_team_rank(2009, "SK") is None
    assert final_team_rank(2025, "없는 팀") is None
