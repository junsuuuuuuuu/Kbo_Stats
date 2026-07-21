"""KBO 2026 등록 로스터 parser의 네트워크 비종속 회귀 테스트."""

import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIRECTORY = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIRECTORY))
MODULE_PATH = SCRIPTS_DIRECTORY / "fetch_kbo_2026_rosters.py"
SPEC = importlib.util.spec_from_file_location("fetch_kbo_2026_rosters", MODULE_PATH)
assert SPEC and SPEC.loader
scraper = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scraper
SPEC.loader.exec_module(scraper)


def test_parse_roster_excludes_staff_and_entry_changes() -> None:
    def table(position: str, player_id: int, name: str) -> str:
        return f"""
        <table class="tNData"><thead><tr>
          <th>등번호</th><th>{position}</th><th>투타유형</th>
          <th>생년월일</th><th>체격</th>
        </tr></thead><tbody><tr>
          <td>18</td><td><a href="/player?playerId={player_id}">{name}</a></td>
          <td>우투우타</td><td>2000-04-06</td><td>183cm, 92kg</td>
        </tr></tbody></table>
        """

    page = (
        '<span id="x_lblGameDate">2026.07.20(월)</span>'
        + table("감독", 1, "감독")
        + table("투수", 69446, "원태인")
        + '<div id="cphContents_cphContents_cphContents_pnlEntryY">'
        + table("내야수", 2, "변동 선수")
    )

    records = scraper.parse_roster(page, "SS")

    assert records == [
        {
            "Season": 2026,
            "AsOfDate": "2026-07-20",
            "TeamCode": "SS",
            "Team": "삼성",
            "PlayerId": 69446,
            "Player": "원태인",
            "Position": "P",
            "UniformNumber": "18",
            "BatThrow": "우투우타",
            "Born": "2000-04-06",
            "HtWt": "183cm, 92kg",
            "URL": "https://www.koreabaseball.com/player?playerId=69446",
            "IsActive": True,
        }
    ]


def test_player_id_rejects_missing_query_value() -> None:
    try:
        scraper.player_id_from_url("https://example.test/player")
    except ValueError as error:
        assert "선수 ID" in str(error)
    else:
        raise AssertionError("playerId가 없으면 ValueError가 필요합니다.")
