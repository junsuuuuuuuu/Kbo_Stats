"""KBO 공식 월별 일정 API에서 구단의 경기 결과를 읽는다."""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser

import httpx

from app.services.cache import BoundedTTLCache
from app.services.kbo_game_log import KBO_BASE_URL, USER_AGENT

SCHEDULE_PATH = "/Schedule/Schedule.aspx"
SCHEDULE_API_PATH = "/ws/Schedule.asmx/GetScheduleList"
TEAM_NAMES = {
    "SS": "삼성", "KT": "KT", "LG": "LG", "HT": "KIA", "OB": "두산",
    "HH": "한화", "NC": "NC", "LT": "롯데", "SK": "SSG", "WO": "키움",
}
TEAM_CODES_BY_NAME = {name: code for code, name in TEAM_NAMES.items()}
_DATE_PATTERN = re.compile(r"^(\d{2})\.(\d{2})")
_HREF_PATTERN = re.compile(r"href=['\"]([^'\"]+)")
_GAME_ID_PATTERN = re.compile(r"[?&]gameId=([A-Z0-9]+)")
_VALID_GAME_ID = re.compile(r"^\d{8}[A-Z0-9]{5,8}$")
logger = logging.getLogger("kbo_api")


class _FragmentTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


@dataclass(frozen=True, slots=True)
class TeamGameResult:
    game_date: str
    opponent: str
    venue: str
    result: str
    team_score: int
    opponent_score: int
    stadium: str
    game_url: str | None
    game_id: str | None


@dataclass(frozen=True, slots=True)
class GameHitter:
    batting_order: str
    position: str
    player_name: str
    at_bats: int
    hits: int
    runs_batted_in: int
    runs: int
    batting_average: float
    plate_appearances: list[str]


@dataclass(frozen=True, slots=True)
class GamePitcher:
    player_name: str
    appearance: str
    result: str | None
    wins: int
    losses: int
    saves: int
    innings_pitched: str
    batters_faced: int
    pitches: int
    at_bats: int
    hits_allowed: int
    home_runs_allowed: int
    walks_and_hit_batters: int
    strikeouts: int
    runs_allowed: int
    earned_runs: int
    earned_run_average: float


@dataclass(frozen=True, slots=True)
class GameTeamBox:
    team_code: str
    team_name: str
    result: str
    runs: int
    hits: int
    errors: int
    walks: int
    innings: list[str]
    hitters: list[GameHitter]
    pitchers: list[GamePitcher]


@dataclass(frozen=True, slots=True)
class TeamGameDetail:
    game_id: str
    game_date: str
    stadium: str
    crowd: str
    start_time: str
    end_time: str
    duration: str
    away: GameTeamBox
    home: GameTeamBox
    key_events: list[tuple[str, str]]
    source_url: str


@dataclass(frozen=True, slots=True)
class GameDayStar:
    player_name: str
    summary: str


@dataclass(frozen=True, slots=True)
class GameDayTeam:
    team_code: str
    team_name: str
    result: str | None
    runs: int | None
    hits: int | None
    errors: int | None


@dataclass(frozen=True, slots=True)
class LatestGameSummary:
    game_id: str
    stadium: str
    start_time: str
    status: str
    away: GameDayTeam
    home: GameDayTeam
    away_hitter: GameDayStar | None
    away_pitcher: GameDayStar | None
    home_hitter: GameDayStar | None
    home_pitcher: GameDayStar | None
    winning_pitcher: str | None
    losing_pitcher: str | None
    cancellation_reason: str | None
    away_starting_pitcher: str | None
    home_starting_pitcher: str | None


@dataclass(frozen=True, slots=True)
class LatestGameDay:
    game_date: str
    games: list[LatestGameSummary]
    source_url: str


@dataclass(frozen=True, slots=True)
class _ScheduledGame:
    game_id: str
    start_time: str
    stadium: str
    away_name: str
    home_name: str
    away_score: int | None
    home_score: int | None
    cancellation_reason: str | None


def _fragment_parts(fragment: str) -> list[str]:
    parser = _FragmentTextParser()
    parser.feed(fragment)
    return parser.parts


def parse_team_schedule_rows(
    rows: list[dict[str, object]], *, season: int, team_name: str
) -> list[TeamGameResult]:
    """일정 API의 표 셀 JSON에서 종료된 해당 구단 경기만 추출한다."""

    results: list[TeamGameResult] = []
    current_date: str | None = None
    for wrapped in rows:
        cells = wrapped.get("row")
        if not isinstance(cells, list):
            continue
        texts = [str(cell.get("Text", "")) for cell in cells if isinstance(cell, dict)]
        if not texts:
            continue
        first_parts = _fragment_parts(texts[0])
        date_match = _DATE_PATTERN.match(first_parts[0]) if first_parts else None
        if date_match:
            month, day = date_match.groups()
            current_date = f"{season}-{month}-{day}"

        play_index = next(
            (
                index for index, cell in enumerate(cells)
                if isinstance(cell, dict) and cell.get("Class") == "play"
            ),
            None,
        )
        if current_date is None or play_index is None:
            continue
        play = _fragment_parts(texts[play_index])
        if len(play) != 5 or play[2].lower() != "vs":
            continue
        away, away_score_text, _, home_score_text, home = play
        try:
            away_score, home_score = int(away_score_text), int(home_score_text)
        except ValueError:
            continue
        if team_name not in {away, home}:
            continue

        is_home = home == team_name
        team_score = home_score if is_home else away_score
        opponent_score = away_score if is_home else home_score
        if team_score == opponent_score:
            result = "D"
        else:
            result = "W" if team_score > opponent_score else "L"
        relay_text = texts[play_index + 1] if play_index + 1 < len(texts) else ""
        href_match = _HREF_PATTERN.search(relay_text)
        game_url = f"{KBO_BASE_URL}{href_match.group(1)}" if href_match else None
        game_id_match = _GAME_ID_PATTERN.search(game_url or "")
        stadium_index = play_index + 5
        stadium_parts = (
            _fragment_parts(texts[stadium_index]) if stadium_index < len(texts) else []
        )
        stadium = stadium_parts[0] if stadium_parts else "—"
        results.append(
            TeamGameResult(
                game_date=current_date,
                opponent=away if is_home else home,
                venue="home" if is_home else "away",
                result=result,
                team_score=team_score,
                opponent_score=opponent_score,
                stadium=stadium,
                game_url=game_url,
                game_id=game_id_match.group(1) if game_id_match else None,
            )
        )
    return results


def parse_game_day_rows(
    rows: list[dict[str, object]], *, season: int, target_date: str
) -> list[_ScheduledGame]:
    games: list[_ScheduledGame] = []
    current_date: str | None = None
    for wrapped in rows:
        cells = wrapped.get("row")
        if not isinstance(cells, list):
            continue
        texts = [str(cell.get("Text", "")) for cell in cells if isinstance(cell, dict)]
        if not texts:
            continue
        first_parts = _fragment_parts(texts[0])
        date_match = _DATE_PATTERN.match(first_parts[0]) if first_parts else None
        if date_match:
            month, day = date_match.groups()
            current_date = f"{season}-{month}-{day}"
        if current_date != target_date:
            continue
        play_index = next(
            (
                index
                for index, cell in enumerate(cells)
                if isinstance(cell, dict) and cell.get("Class") == "play"
            ),
            None,
        )
        if play_index is None:
            continue
        play = _fragment_parts(texts[play_index])
        if len(play) not in {3, 5} or play[len(play) // 2].lower() != "vs":
            continue
        away_name, home_name = play[0], play[-1]
        if away_name not in TEAM_CODES_BY_NAME or home_name not in TEAM_CODES_BY_NAME:
            continue
        relay_text = texts[play_index + 1] if play_index + 1 < len(texts) else ""
        game_id_match = _GAME_ID_PATTERN.search(relay_text)
        cancellation_reason = next(
            (
                part
                for text in texts
                for part in _fragment_parts(text)
                if "취소" in part
            ),
            None,
        )
        game_id = (
            game_id_match.group(1)
            if game_id_match
            else (
                f"{target_date.replace('-', '')}{TEAM_CODES_BY_NAME[away_name]}"
                f"{TEAM_CODES_BY_NAME[home_name]}0"
            )
        )
        stadium_index = play_index + 5
        stadium_parts = (
            _fragment_parts(texts[stadium_index]) if stadium_index < len(texts) else []
        )
        time_parts = _fragment_parts(texts[play_index - 1]) if play_index > 0 else []
        games.append(
            _ScheduledGame(
                game_id=game_id,
                start_time=time_parts[0] if time_parts else "—",
                stadium=stadium_parts[0] if stadium_parts else "—",
                away_name=away_name,
                home_name=home_name,
                away_score=int(play[1]) if len(play) == 5 else None,
                home_score=int(play[3]) if len(play) == 5 else None,
                cancellation_reason=cancellation_reason,
            )
        )
    return games


class KboTeamScheduleClient:
    def __init__(self, ttl_seconds: int = 900, max_cache_size: int = 256) -> None:
        self._cache = BoundedTTLCache[tuple[str, int], list[TeamGameResult]](
            max_size=32, ttl_seconds=ttl_seconds
        )
        self._detail_cache = BoundedTTLCache[str, TeamGameDetail](
            max_size=max_cache_size, ttl_seconds=ttl_seconds
        )
        self._latest_cache = BoundedTTLCache[int, LatestGameDay](
            max_size=8, ttl_seconds=ttl_seconds
        )
        self._day_cache = BoundedTTLCache[str, LatestGameDay](
            max_size=64, ttl_seconds=ttl_seconds
        )

    def results(self, team_code: str, season: int) -> list[TeamGameResult]:
        normalized = team_code.strip().upper()
        team_name = TEAM_NAMES[normalized]
        key = (normalized, season)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        final_month = min(date.today().month, 10) if season == date.today().year else 10
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{KBO_BASE_URL}{SCHEDULE_PATH}",
        }
        games: list[TeamGameResult] = []
        with httpx.Client(headers=headers, timeout=12.0, follow_redirects=True) as client:
            client.get(f"{KBO_BASE_URL}{SCHEDULE_PATH}").raise_for_status()
            successful_months = 0
            for month in range(3, final_month + 1):
                try:
                    response = client.post(
                        f"{KBO_BASE_URL}{SCHEDULE_API_PATH}",
                        data={
                            "leId": "1", "srIdList": "0,9,6", "seasonId": str(season),
                            "gameMonth": f"{month:02d}", "teamId": normalized,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise ValueError("KBO 일정 API 응답 형식이 올바르지 않습니다.")
                except (httpx.HTTPError, ValueError) as exception:
                    logger.warning(
                        "kbo_schedule_month_failed team=%s season=%s month=%s error=%s",
                        normalized,
                        season,
                        month,
                        exception,
                    )
                    continue
                successful_months += 1
                games.extend(
                    parse_team_schedule_rows(
                        payload.get("rows", []), season=season, team_name=team_name
                    )
                )
        if successful_months == 0:
            raise ValueError("KBO 일정 API의 모든 월별 요청이 실패했습니다.")
        games.sort(key=lambda game: game.game_date, reverse=True)
        self._cache.set(key, games)
        return games

    @staticmethod
    def _table(value: str) -> dict[str, object]:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("KBO 박스스코어 표 형식이 올바르지 않습니다.")
        return parsed

    @staticmethod
    def _rows(table: dict[str, object], key: str = "rows") -> list[list[str]]:
        raw_rows = table.get(key, [])
        if not isinstance(raw_rows, list):
            return []
        results: list[list[str]] = []
        for wrapped in raw_rows:
            if not isinstance(wrapped, dict) or not isinstance(wrapped.get("row"), list):
                continue
            results.append([
                " ".join(_fragment_parts(str(cell.get("Text", ""))))
                for cell in wrapped["row"]
                if isinstance(cell, dict)
            ])
        return results

    def _team_box(
        self,
        *,
        index: int,
        score: dict[str, object],
        box: dict[str, object],
    ) -> GameTeamBox:
        is_away = index == 0
        code = str(score["AWAY_ID" if is_away else "HOME_ID"])
        name = str(score["AWAY_NM" if is_away else "HOME_NM"])
        totals = self._rows(self._table(str(score["table3"])))
        inning_rows = self._rows(self._table(str(score["table2"])))
        max_inning = int(box.get("realMaxInning", 9))

        hitter_group = box["arrHitter"][index]  # type: ignore[index]
        identity_rows = self._rows(self._table(str(hitter_group["table1"])))
        stat_rows = self._rows(self._table(str(hitter_group["table3"])))
        appearance_rows = self._rows(self._table(str(hitter_group["table2"])))
        hitters: list[GameHitter] = []
        for identity, stats, appearances in zip(
            identity_rows, stat_rows, appearance_rows, strict=False
        ):
            if len(identity) < 3 or len(stats) < 5:
                continue
            hitters.append(GameHitter(
                batting_order=identity[0], position=identity[1], player_name=identity[2],
                at_bats=int(stats[0]), hits=int(stats[1]), runs_batted_in=int(stats[2]),
                runs=int(stats[3]), batting_average=float(stats[4]),
                plate_appearances=[value for value in appearances if value],
            ))

        pitcher_group = box["arrPitcher"][index]  # type: ignore[index]
        pitcher_rows = self._rows(self._table(str(pitcher_group["table"])))
        pitchers: list[GamePitcher] = []
        for values in pitcher_rows:
            if len(values) < 17:
                continue
            pitchers.append(GamePitcher(
                player_name=values[0], appearance=values[1],
                result=None if not values[2] or values[2] == "&nbsp;" else values[2],
                wins=int(values[3]), losses=int(values[4]), saves=int(values[5]),
                innings_pitched=values[6], batters_faced=int(values[7]), pitches=int(values[8]),
                at_bats=int(values[9]), hits_allowed=int(values[10]),
                home_runs_allowed=int(values[11]), walks_and_hit_batters=int(values[12]),
                strikeouts=int(values[13]), runs_allowed=int(values[14]),
                earned_runs=int(values[15]), earned_run_average=float(values[16]),
            ))

        team_totals = totals[index]
        team_result = "D"
        other_totals = totals[1 - index]
        if int(team_totals[0]) != int(other_totals[0]):
            team_result = "W" if int(team_totals[0]) > int(other_totals[0]) else "L"
        return GameTeamBox(
            team_code=code, team_name=name, result=team_result,
            runs=int(team_totals[0]), hits=int(team_totals[1]), errors=int(team_totals[2]),
            walks=int(team_totals[3]), innings=inning_rows[index][:max_inning],
            hitters=hitters, pitchers=pitchers,
        )

    def game_detail(self, game_id: str, season: int) -> TeamGameDetail:
        if not _VALID_GAME_ID.fullmatch(game_id):
            raise ValueError("올바르지 않은 KBO 경기 ID입니다.")
        cached = self._detail_cache.get(game_id)
        if cached is not None:
            return cached

        game_date = game_id[:8]
        main_url = (
            f"{KBO_BASE_URL}/Schedule/GameCenter/Main.aspx?gameDate={game_date}"
            f"&gameId={game_id}&section=REVIEW"
        )
        headers = {
            "User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9",
            "X-Requested-With": "XMLHttpRequest", "Referer": main_url,
        }
        form = {"leId": "1", "srId": "0", "seasonId": str(season), "gameId": game_id}
        with httpx.Client(headers=headers, timeout=12.0, follow_redirects=True) as client:
            client.get(main_url).raise_for_status()
            score_response = client.post(
                f"{KBO_BASE_URL}/ws/Schedule.asmx/GetScoreBoardScroll", data=form
            )
            box_response = client.post(
                f"{KBO_BASE_URL}/ws/Schedule.asmx/GetBoxScoreScroll", data=form
            )
            score_response.raise_for_status()
            box_response.raise_for_status()
            score, box = score_response.json(), box_response.json()
        if score.get("code") != "100" or box.get("code") != "100":
            raise ValueError("KBO 경기 상세 기록을 찾을 수 없습니다.")
        events = [
            (row[0], row[1])
            for row in self._rows(self._table(str(box["tableEtc"])))
            if len(row) >= 2
        ]
        detail = TeamGameDetail(
            game_id=game_id, game_date=str(score["G_DT"]), stadium=str(score["S_NM"]),
            crowd=str(score["CROWD_CN"]), start_time=str(score["START_TM"]),
            end_time=str(score["END_TM"]), duration=str(score["USE_TM"]),
            away=self._team_box(index=0, score=score, box=box),
            home=self._team_box(index=1, score=score, box=box),
            key_events=events, source_url=main_url,
        )
        self._detail_cache.set(game_id, detail)
        return detail

    @staticmethod
    def _hitter_star(team: GameTeamBox) -> GameDayStar:
        hitter = max(
            team.hitters,
            key=lambda player: (
                player.hits * 3 + player.runs_batted_in * 2 + player.runs,
                player.hits,
                player.runs_batted_in,
                player.runs,
            ),
        )
        return GameDayStar(
            player_name=hitter.player_name,
            summary=f"{hitter.at_bats}타수 {hitter.hits}안타 {hitter.runs_batted_in}타점",
        )

    @staticmethod
    def _pitcher_star(team: GameTeamBox) -> GameDayStar:
        result_priority = {"승": 3, "세": 2, "홀": 1}
        pitcher = max(
            team.pitchers,
            key=lambda player: (
                result_priority.get(player.result or "", 0),
                player.batters_faced,
                player.strikeouts,
                -player.earned_runs,
                -player.hits_allowed,
            ),
        )
        result = f" · {pitcher.result}" if pitcher.result else ""
        return GameDayStar(
            player_name=pitcher.player_name,
            summary=(
                f"{pitcher.innings_pitched}이닝 {pitcher.earned_runs}자책 "
                f"{pitcher.strikeouts}삼진{result}"
            ),
        )

    @staticmethod
    def _decision_pitcher(detail: TeamGameDetail, decision: str) -> str | None:
        return next(
            (
                pitcher.player_name
                for team in (detail.away, detail.home)
                for pitcher in team.pitchers
                if pitcher.result == decision
            ),
            None,
        )

    @staticmethod
    def _day_team(team: GameTeamBox) -> GameDayTeam:
        return GameDayTeam(
            team_code=team.team_code,
            team_name=team.team_name,
            result=team.result,
            runs=team.runs,
            hits=team.hits,
            errors=team.errors,
        )

    def _game_summary(self, detail: TeamGameDetail) -> LatestGameSummary:
        away_starter = next(
            (
                pitcher.player_name
                for pitcher in detail.away.pitchers
                if "선발" in pitcher.appearance
            ),
            None,
        )
        home_starter = next(
            (
                pitcher.player_name
                for pitcher in detail.home.pitchers
                if "선발" in pitcher.appearance
            ),
            None,
        )
        return LatestGameSummary(
            game_id=detail.game_id,
            stadium=detail.stadium,
            start_time=detail.start_time,
            status="completed",
            away=self._day_team(detail.away),
            home=self._day_team(detail.home),
            away_hitter=self._hitter_star(detail.away),
            away_pitcher=self._pitcher_star(detail.away),
            home_hitter=self._hitter_star(detail.home),
            home_pitcher=self._pitcher_star(detail.home),
            winning_pitcher=self._decision_pitcher(detail, "승"),
            losing_pitcher=self._decision_pitcher(detail, "패"),
            cancellation_reason=None,
            away_starting_pitcher=away_starter,
            home_starting_pitcher=home_starter,
        )

    def latest_game_day(self, season: int) -> LatestGameDay:
        cached = self._latest_cache.get(season)
        if cached is not None:
            return cached

        final_month = min(date.today().month, 10) if season == date.today().year else 10
        schedule_url = f"{KBO_BASE_URL}{SCHEDULE_PATH}"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": schedule_url,
        }
        dated_game_ids: dict[str, set[str]] = {}
        with httpx.Client(headers=headers, timeout=12.0, follow_redirects=True) as client:
            client.get(schedule_url).raise_for_status()
            for month in range(final_month, 2, -1):
                response = client.post(
                    f"{KBO_BASE_URL}{SCHEDULE_API_PATH}",
                    data={
                        "leId": "1",
                        "srIdList": "0,9,6",
                        "seasonId": str(season),
                        "gameMonth": f"{month:02d}",
                        "teamId": "",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                rows = payload.get("rows", []) if isinstance(payload, dict) else []
                for team_name in TEAM_NAMES.values():
                    for game in parse_team_schedule_rows(
                        rows, season=season, team_name=team_name
                    ):
                        if game.game_id:
                            dated_game_ids.setdefault(game.game_date, set()).add(game.game_id)
                if dated_game_ids:
                    break
        if not dated_game_ids:
            raise ValueError("완료된 KBO 경기를 찾을 수 없습니다.")

        latest_date = max(dated_game_ids)
        # Reuse the day collector so failed box-score requests retain the basic score.
        result = self.game_day(latest_date, season)
        self._latest_cache.set(season, result)
        return result

    def game_day(self, target_date: str, season: int) -> LatestGameDay:
        parsed_date = date.fromisoformat(target_date)
        if parsed_date.year != season:
            raise ValueError("조회 날짜와 시즌이 일치하지 않습니다.")
        cached = self._day_cache.get(target_date)
        if cached is not None:
            return cached

        schedule_url = f"{KBO_BASE_URL}{SCHEDULE_PATH}"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": schedule_url,
        }
        with httpx.Client(headers=headers, timeout=12.0, follow_redirects=True) as client:
            client.get(schedule_url).raise_for_status()
            response = client.post(
                f"{KBO_BASE_URL}{SCHEDULE_API_PATH}",
                data={
                    "leId": "1",
                    "srIdList": "0,9,6",
                    "seasonId": str(season),
                    "gameMonth": f"{parsed_date.month:02d}",
                    "teamId": "",
                },
            )
            response.raise_for_status()
            payload = response.json()
            game_list_response = client.post(
                f"{KBO_BASE_URL}/ws/Main.asmx/GetKboGameList",
                data={
                    "leId": "1",
                    "srId": "0,1,3,4,5,6,7,8,9",
                    "date": target_date.replace("-", ""),
                },
            )
            game_list_response.raise_for_status()
            game_list_payload = game_list_response.json()
        rows = payload.get("rows", []) if isinstance(payload, dict) else []
        game_list = (
            game_list_payload.get("game", []) if isinstance(game_list_payload, dict) else []
        )
        pitchers_by_game = {
            str(game.get("G_ID")): (
                str(game.get("T_PIT_P_NM") or "").strip() or None,
                str(game.get("B_PIT_P_NM") or "").strip() or None,
            )
            for game in game_list
            if isinstance(game, dict) and game.get("G_ID")
        }
        scheduled_games = parse_game_day_rows(rows, season=season, target_date=target_date)
        completed = [game for game in scheduled_games if game.away_score is not None]
        details_by_id: dict[str, TeamGameDetail] = {}
        if completed:
            with ThreadPoolExecutor(max_workers=min(5, len(completed))) as executor:
                futures = {
                    executor.submit(self.game_detail, game.game_id, season): game.game_id
                    for game in completed
                }
                for future in as_completed(futures):
                    try:
                        detail = future.result()
                        details_by_id[detail.game_id] = detail
                    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exception:
                        logger.warning(
                            "kbo_game_detail_failed game_id=%s error=%s",
                            futures[future],
                            exception,
                        )

        summaries: list[LatestGameSummary] = []
        for game in scheduled_games:
            detail = details_by_id.get(game.game_id)
            if detail:
                summaries.append(self._game_summary(detail))
                continue
            away_result = home_result = None
            if game.away_score is not None and game.home_score is not None:
                away_result = "D" if game.away_score == game.home_score else (
                    "W" if game.away_score > game.home_score else "L"
                )
                home_result = "D" if away_result == "D" else ("L" if away_result == "W" else "W")
            summaries.append(
                LatestGameSummary(
                    game_id=game.game_id,
                    stadium=game.stadium,
                    start_time=game.start_time,
                    status=(
                        "cancelled" if game.cancellation_reason else
                        "completed" if game.away_score is not None else "scheduled"
                    ),
                    away=GameDayTeam(
                        TEAM_CODES_BY_NAME[game.away_name], game.away_name,
                        away_result, game.away_score, None, None
                    ),
                    home=GameDayTeam(
                        TEAM_CODES_BY_NAME[game.home_name], game.home_name,
                        home_result, game.home_score, None, None
                    ),
                    away_hitter=None,
                    away_pitcher=None,
                    home_hitter=None,
                    home_pitcher=None,
                    winning_pitcher=None,
                    losing_pitcher=None,
                    cancellation_reason=game.cancellation_reason,
                    away_starting_pitcher=pitchers_by_game.get(game.game_id, (None, None))[0],
                    home_starting_pitcher=pitchers_by_game.get(game.game_id, (None, None))[1],
                )
            )
        result = LatestGameDay(target_date, summaries, schedule_url)
        self._day_cache.set(target_date, result)
        return result


kbo_team_schedule_client = KboTeamScheduleClient()
