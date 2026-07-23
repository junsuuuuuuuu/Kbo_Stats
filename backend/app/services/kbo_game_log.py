"""KBO 공식 선수 페이지에서 시즌별 투수 등판 기록을 읽는다."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

from app.services.cache import BoundedTTLCache

KBO_BASE_URL = "https://www.koreabaseball.com"
DAILY_PATH = "/Record/Player/PitcherDetail/Daily.aspx"
HITTER_DAILY_PATH = "/Record/Player/HitterDetail/Daily.aspx"
USER_AGENT = "KBO-AI-Player-Analytics/1.0 (player game log)"
_DATE_PATTERN = re.compile(r"^(\d{2})\.(\d{2})$")


class _TableRowParser(HTMLParser):
    """HTML의 모든 표 행을 셀 텍스트 배열로 단순화한다."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None and data.strip():
            self._cell.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(" ".join(" ".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


@dataclass(frozen=True, slots=True)
class PitchingAppearance:
    game_date: str
    opponent: str
    appearance_type: str
    result: str | None
    game_era: float
    batters_faced: int
    innings_pitched: str
    hits_allowed: int
    home_runs_allowed: int
    walks_allowed: int
    hit_batters: int
    strikeouts: int
    runs_allowed: int
    earned_runs: int
    season_era: float


@dataclass(frozen=True, slots=True)
class BattingAppearance:
    game_date: str
    opponent: str
    game_average: float | None
    plate_appearances: int
    at_bats: int
    runs: int
    hits: int
    doubles: int
    triples: int
    home_runs: int
    runs_batted_in: int
    stolen_bases: int
    caught_stealing: int
    walks: int
    hit_by_pitch: int
    strikeouts: int
    grounded_into_double_play: int
    season_average: float


def parse_pitching_appearances(page: str, season: int) -> list[PitchingAppearance]:
    """일자별 성적 표에서 합계/헤더 행을 제외한 실제 등판만 추출한다."""

    parser = _TableRowParser()
    parser.feed(page)
    appearances: list[PitchingAppearance] = []
    for cells in parser.rows:
        match = _DATE_PATTERN.fullmatch(cells[0]) if len(cells) >= 15 else None
        if match is None:
            continue
        month, day = match.groups()
        appearances.append(
            PitchingAppearance(
                game_date=f"{season}-{month}-{day}",
                opponent=cells[1],
                appearance_type=cells[2],
                result=cells[3] or None,
                game_era=float(cells[4]),
                batters_faced=int(cells[5]),
                innings_pitched=cells[6],
                hits_allowed=int(cells[7]),
                home_runs_allowed=int(cells[8]),
                walks_allowed=int(cells[9]),
                hit_batters=int(cells[10]),
                strikeouts=int(cells[11]),
                runs_allowed=int(cells[12]),
                earned_runs=int(cells[13]),
                season_era=float(cells[14]),
            )
        )
    return appearances


def parse_batting_appearances(page: str, season: int) -> list[BattingAppearance]:
    """타자 일자별 성적 표에서 실제 출장 행을 모두 추출한다."""

    parser = _TableRowParser()
    parser.feed(page)
    appearances: list[BattingAppearance] = []
    for cells in parser.rows:
        match = _DATE_PATTERN.fullmatch(cells[0]) if len(cells) >= 18 else None
        if match is None:
            continue
        month, day = match.groups()
        appearances.append(
            BattingAppearance(
                game_date=f"{season}-{month}-{day}",
                opponent=cells[1],
                game_average=None if cells[2] == "-" else float(cells[2]),
                plate_appearances=int(cells[3]),
                at_bats=int(cells[4]),
                runs=int(cells[5]),
                hits=int(cells[6]),
                doubles=int(cells[7]),
                triples=int(cells[8]),
                home_runs=int(cells[9]),
                runs_batted_in=int(cells[10]),
                stolen_bases=int(cells[11]),
                caught_stealing=int(cells[12]),
                walks=int(cells[13]),
                hit_by_pitch=int(cells[14]),
                strikeouts=int(cells[15]),
                grounded_into_double_play=int(cells[16]),
                season_average=float(cells[17]),
            )
        )
    return appearances


class KboGameLogClient:
    """짧은 TTL 캐시를 둔 KBO 일자별 기록 클라이언트."""

    def __init__(self, ttl_seconds: int = 900, max_cache_size: int = 512) -> None:
        self._cache = BoundedTTLCache[tuple[str, int, int], list[object]](
            max_size=max_cache_size,
            ttl_seconds=ttl_seconds,
        )

    def pitching_appearances(self, player_id: int, season: int) -> list[PitchingAppearance]:
        key = ("pitching", player_id, season)
        cached = self._cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        response = httpx.get(
            f"{KBO_BASE_URL}{DAILY_PATH}",
            params={"playerId": player_id},
            headers={"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"},
            timeout=12.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        appearances = parse_pitching_appearances(response.content.decode("utf-8"), season)
        self._cache.set(key, appearances)
        return appearances

    def batting_appearances(self, player_id: int, season: int) -> list[BattingAppearance]:
        key = ("batting", player_id, season)
        cached = self._cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        response = httpx.get(
            f"{KBO_BASE_URL}{HITTER_DAILY_PATH}",
            params={"playerId": player_id},
            headers={"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"},
            timeout=12.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        appearances = parse_batting_appearances(response.content.decode("utf-8"), season)
        self._cache.set(key, appearances)
        return appearances


kbo_game_log_client = KboGameLogClient()
