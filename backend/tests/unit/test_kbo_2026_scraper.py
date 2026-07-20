"""KBO 2026 snapshot parser의 네트워크 비종속 회귀 테스트."""

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[3] / "scripts" / "fetch_kbo_2026.py"
SPEC = importlib.util.spec_from_file_location("fetch_kbo_2026", MODULE_PATH)
assert SPEC and SPEC.loader
scraper = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scraper
SPEC.loader.exec_module(scraper)


def test_parse_table_uses_player_id_and_data_id() -> None:
    page = """
    <table><tbody><tr>
      <td>1</td>
      <td><a href="/Record/Player/HitterDetail/Basic.aspx?playerId=12345">테스트 선수</a></td>
      <td>테스트팀</td>
      <td data-id="HRA_RT">0.321</td>
      <td data-id="GAME_CN">42</td>
    </tr></tbody></table>
    """

    records = scraper.parse_table(page, scraper.HITTER_STAT_MAP)

    assert records == [
        {
            "Id": "12345",
            "URL": "https://www.koreabaseball.com/Record/Player/HitterDetail/Basic.aspx?playerId=12345",
            "Player": "테스트 선수",
            "Team": "테스트팀",
            "AVG": "0.321",
            "G": "42",
        }
    ]


def test_next_page_target_stops_on_last_page() -> None:
    first = """
    <div class="paging">
      <a class="on" href="javascript:__doPostBack(&#39;page1&#39;,&#39;&#39;)">1</a>
      <a href="javascript:__doPostBack(&#39;page2&#39;,&#39;&#39;)">2</a>
    </div>
    """
    last = first.replace('class="on" href="javascript:__doPostBack(&#39;page1',
                         'href="javascript:__doPostBack(&#39;page1').replace(
        '<a href="javascript:__doPostBack(&#39;page2',
        '<a class="on" href="javascript:__doPostBack(&#39;page2',
    )

    assert scraper.next_page_target(first) == "page2"
    assert scraper.next_page_target(last) is None


def test_scrape_endpoint_resets_to_first_page_before_each_team(monkeypatch) -> None:
    crawler = object.__new__(scraper.KboCrawler)
    team_source_pages: list[str] = []
    monkeypatch.setattr(scraper, "TEAM_CODES", ("SS", "KT"))
    monkeypatch.setattr(crawler, "request", lambda method, path: "landing-page")

    def fake_postback(path, page, event_target, overrides=None):
        if event_target == scraper.SEASON_FIELD:
            return "season-first-page"
        team_source_pages.append(page)
        player_id = "1" if overrides[scraper.TEAM_FIELD] == "SS" else "2"
        return f"""
        <table><tbody><tr>
          <td>1</td>
          <td><a href="/player?playerId={player_id}">선수 {player_id}</a></td>
          <td>팀</td><td data-id="GAME_CN">1</td>
        </tr></tbody></table>
        """

    monkeypatch.setattr(crawler, "postback", fake_postback)

    records = crawler.scrape_endpoint("/records", scraper.HITTER_STAT_MAP)

    assert team_source_pages == ["season-first-page", "season-first-page"]
    assert {record["Id"] for record in records} == {"1", "2"}


def test_profile_parser_and_role_mapping() -> None:
    page = """
    <div class="player_basic"><ul>
      <li><strong>선수명: </strong>신인 선수</li>
      <li><strong>생년월일: </strong>2005년 03월 04일</li>
      <li><strong>포지션: </strong>외야수(우투좌타)</li>
      <li><strong>신장/체중: </strong>180cm/80kg</li>
    </ul></div>
    """

    profile = scraper.profile_from_detail(scraper.parse_profile(page), "batting")

    assert profile["Player"] == "신인 선수"
    assert profile["Born"] == "2005-03-04"
    assert profile["Age"] == 21
    assert profile["Position"] == "OF"
    assert profile["BatThrow"] == "L/R"
