from app.services.kbo_team_schedule import parse_game_day_rows, parse_team_schedule_rows


def _cell(text: str, class_name: str | None = None) -> dict[str, str | None]:
    return {"Text": text, "Class": class_name}


def test_parse_team_schedule_returns_completed_games_and_skips_future_games() -> None:
    rows = [
        {
            "row": [
                _cell("07.01(수)", "day"),
                _cell("<b>18:30</b>", "time"),
                _cell(
                    '<span>SSG</span><em><span class="same">6</span>'
                    '<span>vs</span><span class="same">6</span></em><span>KIA</span>',
                    "play",
                ),
                _cell(
                    "<a href='/Schedule/GameCenter/Main.aspx?gameDate=20260701"
                    "&gameId=20260701SKHT0&section=REVIEW'>리뷰</a>"
                ),
                _cell(""), _cell(""), _cell(""), _cell("광주"), _cell("-"),
            ]
        },
        {
            "row": [
                _cell("07.02(목)", "day"),
                _cell("18:30", "time"),
                _cell("<span>SSG</span><em><span>vs</span></em><span>KIA</span>", "play"),
            ]
        },
    ]

    games = parse_team_schedule_rows(rows, season=2026, team_name="SSG")

    assert len(games) == 1
    assert games[0].game_date == "2026-07-01"
    assert games[0].opponent == "KIA"
    assert games[0].venue == "away"
    assert games[0].result == "D"
    assert games[0].team_score == 6
    assert games[0].stadium == "광주"
    assert games[0].game_url is not None
    assert games[0].game_id == "20260701SKHT0"


def test_parse_team_schedule_preserves_rowspan_date_for_doubleheader() -> None:
    rows = [
        {
            "row": [
                _cell("06.21(일)", "day"), _cell("14:00", "time"),
                _cell(
                    "<span>두산</span><em><span>2</span><span>vs</span>"
                    "<span>3</span></em><span>LG</span>",
                    "play",
                ),
                _cell(""), _cell(""), _cell(""), _cell(""), _cell("잠실"),
            ]
        },
        {
            "row": [
                _cell("17:00", "time"),
                _cell(
                    "<span>두산</span><em><span>5</span><span>vs</span>"
                    "<span>1</span></em><span>LG</span>",
                    "play",
                ),
                _cell(""), _cell(""), _cell(""), _cell(""), _cell("잠실"),
            ]
        },
    ]

    games = parse_team_schedule_rows(rows, season=2026, team_name="LG")

    assert [game.game_date for game in games] == ["2026-06-21", "2026-06-21"]
    assert [game.result for game in games] == ["W", "L"]


def test_parse_game_day_rows_includes_future_schedule() -> None:
    rows = [{
        "row": [
            _cell("07.22(수)", "day"),
            _cell("18:30", "time"),
            _cell("<span>NC</span><em><span>vs</span></em><span>LG</span>", "play"),
            _cell(
                "<a href='/Schedule/GameCenter/Main.aspx?gameDate=20260722"
                "&gameId=20260722NCLG0&section=START_PIT'>프리뷰</a>"
            ),
            _cell(""), _cell(""), _cell(""), _cell("잠실"),
        ]
    }]

    games = parse_game_day_rows(rows, season=2026, target_date="2026-07-22")

    assert len(games) == 1
    assert games[0].game_id == "20260722NCLG0"
    assert games[0].away_name == "NC"
    assert games[0].home_name == "LG"
    assert games[0].away_score is None
    assert games[0].stadium == "잠실"


def test_parse_game_day_rows_keeps_rainout_without_review_link() -> None:
    rows = [{
        "row": [
            _cell("04.09(목)", "day"),
            _cell("18:30", "time"),
            _cell("<span>키움</span><em><span>vs</span></em><span>두산</span>", "play"),
            _cell("", "relay"),
            _cell(""), _cell(""), _cell(""), _cell("잠실"), _cell("우천취소"),
        ]
    }]

    games = parse_game_day_rows(rows, season=2026, target_date="2026-04-09")

    assert len(games) == 1
    assert games[0].game_id == "20260409WOOB0"
    assert games[0].cancellation_reason == "우천취소"
