"""KBO 투수 일자별 기록 파서 테스트."""

from app.services.kbo_game_log import parse_batting_appearances, parse_pitching_appearances


def test_parse_pitching_appearances_skips_headers_and_totals() -> None:
    page = """
    <table>
      <tr><th>일자</th><th>상대</th><th>구분</th><th>결과</th></tr>
      <tr><td>합계</td><td></td><td></td><td></td></tr>
      <tr>
        <td>04.25</td><td>LG</td><td>구원</td><td>홀</td><td>0.00</td>
        <td>5</td><td>1</td><td>1</td><td>0</td><td>1</td><td>0</td>
        <td>0</td><td>0</td><td>0</td><td>1.80</td>
      </tr>
      <tr>
        <td>04.28</td><td>삼성</td><td>구원</td><td></td><td>27.00</td>
        <td>2</td><td>1/3</td><td>0</td><td>0</td><td>1</td><td>0</td>
        <td>0</td><td>1</td><td>1</td><td>2.61</td>
      </tr>
    </table>
    """

    rows = parse_pitching_appearances(page, 2026)

    assert len(rows) == 2
    assert rows[0].game_date == "2026-04-25"
    assert rows[0].result == "홀"
    assert rows[1].result is None
    assert rows[1].innings_pitched == "1/3"
    assert rows[1].earned_runs == 1


def test_parse_batting_appearances_includes_zero_plate_appearance_games() -> None:
    page = """
    <table>
      <tr>
        <td>05.10</td><td>NC</td><td>0.400</td><td>5</td><td>5</td><td>0</td>
        <td>2</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td>
        <td>0</td><td>0</td><td>3</td><td>0</td><td>0.133</td>
      </tr>
      <tr>
        <td>05.12</td><td>LG</td><td>-</td><td>0</td><td>0</td><td>0</td>
        <td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td>
        <td>0</td><td>0</td><td>0</td><td>0</td><td>0.133</td>
      </tr>
    </table>
    """

    rows = parse_batting_appearances(page, 2026)

    assert len(rows) == 2
    assert rows[0].hits == 2
    assert rows[1].game_date == "2026-05-12"
    assert rows[1].game_average is None
    assert rows[1].plate_appearances == 0
