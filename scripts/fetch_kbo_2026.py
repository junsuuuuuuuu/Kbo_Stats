"""KBO 공식 기록실에서 2026 정규시즌 기록을 저속으로 수집한다.

진행 중 시즌은 기존 1982~2025 원본과 합치지 않고 별도 partial snapshot으로 저장한다.
KBO 페이지는 ASP.NET postback을 사용하므로 hidden form state를 요청마다 갱신한다.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

BASE_URL = "https://www.koreabaseball.com"
SEASON = 2026
TEAM_CODES = ("SS", "KT", "LG", "HT", "OB", "HH", "NC", "LT", "SK", "WO")
SEASON_FIELD = "ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$ddlSeason$ddlSeason"
TEAM_FIELD = "ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$ddlTeam$ddlTeam"
USER_AGENT = "KBO-AI-Player-Analytics/1.0 (educational portfolio; one-time snapshot)"

HITTER_ENDPOINTS = (
    "/Record/Player/HitterBasic/Basic1.aspx",
    "/Record/Player/HitterBasic/Basic2.aspx",
    "/Record/Player/HitterBasic/BasicOld.aspx",
)
PITCHER_ENDPOINTS = (
    "/Record/Player/PitcherBasic/Basic1.aspx",
    "/Record/Player/PitcherBasic/Basic2.aspx",
)

HITTER_COLUMNS = (
    "Id", "URL", "Player", "Age", "Born", "Position", "BatThrow", "HtWt", "Career",
    "Draft", "Season", "Team", "G", "PA", "AB", "R", "H", "2B", "3B", "HR", "TB",
    "RBI", "SB", "CS", "BB", "HBP", "SO", "GDP", "SF", "SH", "E", "AVG", "SLG",
    "OBP", "OPS", "AsOfDate", "IsPartial",
)
PITCHER_COLUMNS = (
    "Id", "URL", "Player", "Age", "Born", "Position", "BatThrow", "HtWt", "Career",
    "Draft", "Season", "Team", "ERA", "G", "CG", "SHO", "W", "L", "SV", "HLD",
    "WPCT", "TBF", "IP", "H", "HR", "BB", "HBP", "SO", "R", "ER", "AsOfDate",
    "IsPartial",
)

HITTER_STAT_MAP = {
    "HRA_RT": "AVG", "GAME_CN": "G", "PA_CN": "PA", "AB_CN": "AB", "RUN_CN": "R",
    "HIT_CN": "H", "H2_CN": "2B", "H3_CN": "3B", "HR_CN": "HR", "TB_CN": "TB",
    "RBI_CN": "RBI", "SB_CN": "SB", "CS_CN": "CS", "BB_CN": "BB", "HP_CN": "HBP",
    "KK_CN": "SO", "GD_CN": "GDP", "SF_CN": "SF", "SH_CN": "SH", "ERR_CN": "E",
    "SLG_RT": "SLG", "OBP_RT": "OBP", "OPS_RT": "OPS",
}
PITCHER_STAT_MAP = {
    "ERA_RT": "ERA", "GAME_CN": "G", "CG_CN": "CG", "SHO_CN": "SHO", "W_CN": "W",
    "L_CN": "L", "SV_CN": "SV", "HOLD_CN": "HLD", "WRA_RT": "WPCT", "PA_CN": "TBF",
    "INN2_CN": "IP", "HIT_CN": "H", "HR_CN": "HR", "BB_CN": "BB", "HP_CN": "HBP",
    "KK_CN": "SO", "R_CN": "R", "ER_CN": "ER",
}


def normalized_text(parts: list[str]) -> str:
    """중첩 태그와 줄바꿈을 하나의 표시 문자열로 정규화한다."""

    return " ".join(" ".join(parts).split())


class FormStateParser(HTMLParser):
    """postback에 필요한 input과 현재 선택된 select 값을 추출한다."""

    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}
        self._select_name: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "input" and attributes.get("name"):
            self.values[str(attributes["name"])] = str(attributes.get("value") or "")
        elif tag == "select":
            self._select_name = attributes.get("name")
        elif tag == "option" and self._select_name and "selected" in attributes:
            self.values[self._select_name] = str(attributes.get("value") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self._select_name = None


@dataclass(slots=True)
class TableCell:
    data_id: str | None
    text: list[str]
    href: str | None = None


class PlayerTableParser(HTMLParser):
    """선수 링크가 포함된 기록 테이블 행만 파싱한다."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[TableCell]] = []
        self._row: list[TableCell] | None = None
        self._cell: TableCell | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = TableCell(attributes.get("data-id"), [])
            self._row.append(self._cell)
        elif tag == "a" and self._cell is not None:
            self._cell.href = attributes.get("href")

    def handle_data(self, data: str) -> None:
        if self._cell is not None and data.strip():
            self._cell.text.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"}:
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(cell.href and "playerId=" in cell.href for cell in self._row):
                self.rows.append(self._row)
            self._row = None


class PlayerProfileParser(HTMLParser):
    """신규 선수의 상세 페이지에서 player_basic 목록을 읽는다."""

    def __init__(self) -> None:
        super().__init__()
        self.items: list[str] = []
        self._in_basic = False
        self._div_depth = 0
        self._item: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "div" and attributes.get("class") == "player_basic":
            self._in_basic = True
            self._div_depth = 1
            return
        if not self._in_basic:
            return
        if tag == "div":
            self._div_depth += 1
        elif tag == "li":
            self._item = []

    def handle_data(self, data: str) -> None:
        if self._item is not None and data.strip():
            self._item.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if not self._in_basic:
            return
        if tag == "li" and self._item is not None:
            self.items.append(normalized_text(self._item))
            self._item = None
        elif tag == "div":
            self._div_depth -= 1
            if self._div_depth == 0:
                self._in_basic = False


class PagerParser(HTMLParser):
    """paging 영역의 숫자 링크와 현재 페이지를 추출한다."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, Any]] = []
        self._in_paging = False
        self._div_depth = 0
        self._anchor: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "div" and "paging" in str(attributes.get("class", "")).split():
            self._in_paging = True
            self._div_depth = 1
            return
        if not self._in_paging:
            return
        if tag == "div":
            self._div_depth += 1
        elif tag == "a":
            self._anchor = {
                "href": str(attributes.get("href") or ""),
                "class": str(attributes.get("class") or ""),
                "text": [],
            }

    def handle_data(self, data: str) -> None:
        if self._anchor is not None and data.strip():
            self._anchor["text"].append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if not self._in_paging:
            return
        if tag == "a" and self._anchor is not None:
            self.links.append(self._anchor)
            self._anchor = None
        elif tag == "div":
            self._div_depth -= 1
            if self._div_depth == 0:
                self._in_paging = False


def form_payload(page: str, event_target: str, overrides: dict[str, str] | None = None) -> dict[str, str]:
    parser = FormStateParser()
    parser.feed(page)
    payload = parser.values
    payload["__EVENTTARGET"] = event_target
    payload["__EVENTARGUMENT"] = ""
    payload.update(overrides or {})
    return payload


def next_page_target(page: str) -> str | None:
    """현재 숫자 페이지 다음의 postback target을 반환한다."""

    parser = PagerParser()
    parser.feed(page)
    numeric_links = []
    for link in parser.links:
        text = normalized_text(link["text"])
        match = re.search(r"__doPostBack\('([^']+)'", html.unescape(link["href"]))
        if text.isdigit() and match:
            numeric_links.append((int(text), match.group(1), link["class"]))
    current = next((number for number, _, css in numeric_links if "on" in css.split()), 1)
    candidates = sorted((number, target) for number, target, _ in numeric_links)
    return next((target for number, target in candidates if number > current), None)


def parse_table(page: str, stat_map: dict[str, str]) -> list[dict[str, str]]:
    parser = PlayerTableParser()
    parser.feed(page)
    records: list[dict[str, str]] = []
    for cells in parser.rows:
        player_cell = next(cell for cell in cells if cell.href and "playerId=" in cell.href)
        player_index = cells.index(player_cell)
        match = re.search(r"playerId=(\d+)", str(player_cell.href))
        if not match or player_index + 1 >= len(cells):
            continue
        record = {
            "Id": match.group(1),
            "URL": urljoin(BASE_URL, str(player_cell.href)),
            "Player": normalized_text(player_cell.text),
            "Team": normalized_text(cells[player_index + 1].text),
        }
        for cell in cells:
            column = stat_map.get(str(cell.data_id))
            if column:
                record[column] = normalized_text(cell.text)
        records.append(record)
    return records


def parse_profile(page: str) -> dict[str, str]:
    parser = PlayerProfileParser()
    parser.feed(page)
    fields: dict[str, str] = {}
    for item in parser.items:
        if ":" not in item:
            continue
        label, value = item.split(":", 1)
        fields[label.strip()] = value.strip()
    return fields


class KboCrawler:
    """요청 간격, retry/backoff와 ASP.NET session을 한 곳에서 관리한다."""

    def __init__(self, delay_seconds: float, timeout_seconds: float = 30.0) -> None:
        self.delay_seconds = delay_seconds
        self._last_request_at = 0.0
        self.request_count = 0
        self.client = httpx.Client(
            base_url=BASE_URL,
            timeout=timeout_seconds,
            follow_redirects=True,
            trust_env=False,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"},
        )

    def close(self) -> None:
        self.client.close()

    def _wait(self) -> None:
        remaining = self.delay_seconds - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)

    def request(self, method: str, path: str, **kwargs: Any) -> str:
        for attempt in range(3):
            self._wait()
            try:
                response = self.client.request(method, path, **kwargs)
                self._last_request_at = time.monotonic()
                self.request_count += 1
                if response.status_code == 429:
                    time.sleep(min(float(response.headers.get("Retry-After", "5")), 60.0))
                    continue
                response.raise_for_status()
                return response.content.decode("utf-8")
            except (httpx.HTTPError, UnicodeDecodeError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("KBO 요청 재시도 횟수를 초과했습니다.")

    def check_robots(self) -> None:
        robots = self.request("GET", "/robots.txt")
        disallowed = [
            line.split(":", 1)[1].strip()
            for line in robots.splitlines()
            if line.lower().startswith("disallow:")
        ]
        if any(path in {"/", "/Record", "/Record/"} for path in disallowed):
            raise RuntimeError("KBO robots.txt가 /Record/ 수집을 허용하지 않습니다.")

    def postback(
        self,
        path: str,
        page: str,
        event_target: str,
        overrides: dict[str, str] | None = None,
    ) -> str:
        return self.request(
            "POST",
            path,
            data=form_payload(page, event_target, overrides),
            headers={"Referer": urljoin(BASE_URL, path)},
        )

    def scrape_endpoint(self, path: str, stat_map: dict[str, str]) -> list[dict[str, str]]:
        """한 기록 화면을 시즌·팀·숫자 페이지 순으로 순회한다."""

        page = self.request("GET", path)
        base_page = self.postback(path, page, SEASON_FIELD, {SEASON_FIELD: str(SEASON)})
        collected: dict[tuple[str, str], dict[str, str]] = {}
        for team_code in TEAM_CODES:
            # Always change the team from the season filter's first page.  If the
            # previous team's last page is reused, ASP.NET keeps that page index
            # and the next team's first 30 players can be skipped.
            page = self.postback(path, base_page, TEAM_FIELD, {TEAM_FIELD: team_code})
            page_number = 1
            while True:
                rows = parse_table(page, stat_map)
                for row in rows:
                    collected[(row["Id"], row["Team"])] = row
                target = next_page_target(page)
                if target is None:
                    break
                page = self.postback(path, page, target)
                page_number += 1
                if page_number > 10:
                    raise RuntimeError(f"비정상적으로 많은 페이지입니다: {path}/{team_code}")
            print(f"  {path} team={team_code} 누적={len(collected)}", flush=True)
        return list(collected.values())


def merge_endpoint_records(endpoint_records: list[list[dict[str, str]]]) -> list[dict[str, str]]:
    merged: dict[tuple[str, str], dict[str, str]] = {}
    for records in endpoint_records:
        for record in records:
            key = (record["Id"], record["Team"])
            target = merged.setdefault(key, {})
            for column, value in record.items():
                if column in target and target[column] not in {"", value} and value:
                    raise ValueError(f"기록 화면 간 값이 다릅니다: {key}/{column}")
                if value or column not in target:
                    target[column] = value
    return list(merged.values())


def historical_profiles(raw_directory: Path) -> dict[str, dict[str, Any]]:
    profile_columns = ["Id", "Player", "Age", "Born", "Position", "BatThrow", "HtWt", "Career", "Draft"]
    frames = []
    profile_sources = list(raw_directory.glob("*1982-2025.csv"))
    profile_sources.extend(raw_directory.glob("*2026_partial.csv"))
    for path in profile_sources:
        frame = pd.read_csv(path, usecols=lambda column: column in {*profile_columns, "Season"}, low_memory=False)
        frames.append(frame)
    if not frames:
        return {}
    combined = pd.concat(frames, ignore_index=True).sort_values("Season")
    latest = combined.drop_duplicates("Id", keep="last")
    return {
        str(int(row["Id"])): {
            column: "" if pd.isna(row.get(column)) else row.get(column)
            for column in profile_columns
        }
        for _, row in latest.iterrows()
    }


def position_and_sides(value: str, role: str) -> tuple[str, str]:
    position_label = value.split("(", 1)[0].strip()
    position_map = {"투수": "P", "포수": "C", "내야수": "IF", "외야수": "OF"}
    sides = ""
    match = re.search(r"\(([^)]+)\)", value)
    if match:
        side_map = {"우투": "R", "좌투": "L", "우타": "R", "좌타": "L", "양타": "S"}
        tokens = re.findall(r"우투|좌투|우타|좌타|양타", match.group(1))
        if len(tokens) >= 2:
            sides = f"{side_map[tokens[1]]}/{side_map[tokens[0]]}"
    return ("P" if role == "pitching" else position_map.get(position_label, position_label), sides)


def profile_from_detail(fields: dict[str, str], role: str) -> dict[str, Any]:
    born_text = fields.get("생년월일", "")
    born_match = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", born_text)
    born = ""
    age: int | str = ""
    if born_match:
        born = f"{int(born_match.group(1)):04d}-{int(born_match.group(2)):02d}-{int(born_match.group(3)):02d}"
        age = SEASON - int(born_match.group(1))
    position, sides = position_and_sides(fields.get("포지션", ""), role)
    return {
        "Player": fields.get("선수명", ""),
        "Age": age,
        "Born": born,
        "Position": position,
        "BatThrow": sides,
        "HtWt": fields.get("신장/체중", ""),
        "Career": fields.get("경력", ""),
        "Draft": fields.get("지명순위", ""),
    }


def enrich_profiles(
    crawler: KboCrawler,
    records_by_role: dict[str, list[dict[str, str]]],
    known_profiles: dict[str, dict[str, Any]],
) -> int:
    missing_urls: dict[str, tuple[str, str]] = {}
    for role, records in records_by_role.items():
        for record in records:
            if record["Id"] not in known_profiles:
                missing_urls.setdefault(record["Id"], (record["URL"], role))

    for index, (player_id, (url, role)) in enumerate(sorted(missing_urls.items()), start=1):
        detail = crawler.request("GET", url.replace(BASE_URL, ""))
        known_profiles[player_id] = profile_from_detail(parse_profile(detail), role)
        if index % 10 == 0 or index == len(missing_urls):
            print(f"  신규 선수 프로필 {index}/{len(missing_urls)}", flush=True)

    for role, records in records_by_role.items():
        for record in records:
            profile = known_profiles.get(record["Id"], {})
            table_name = record["Player"]
            record.update(profile)
            if not record.get("Player"):
                record["Player"] = table_name
            record["Season"] = SEASON
            record["Position"] = "P" if role == "pitching" else record.get("Position", "")
    return len(missing_urls)


def frame_for_output(
    records: list[dict[str, Any]], columns: tuple[str, ...], as_of_date: date
) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    frame["AsOfDate"] = as_of_date.isoformat()
    frame["IsPartial"] = True
    for column in columns:
        if column not in frame:
            frame[column] = ""
    frame["Id"] = pd.to_numeric(frame["Id"], errors="raise").astype("int64")
    frame["Season"] = SEASON
    return frame.loc[:, columns].sort_values(["Player", "Team", "Id"]).reset_index(drop=True)


def validate_snapshot(frame: pd.DataFrame, role: str) -> dict[str, Any]:
    required = ["Id", "Player", "Team", "Season", "G"]
    required += ["PA", "AVG", "OPS"] if role == "batting" else ["IP", "ERA", "SO"]
    missing_counts = {column: int(frame[column].isna().sum() + frame[column].eq("").sum()) for column in required}
    duplicates = int(frame.duplicated(["Id", "Team"]).sum())
    if frame.empty or set(frame["Season"]) != {SEASON} or duplicates or any(missing_counts.values()):
        raise ValueError(
            f"{role} snapshot 검증 실패: rows={len(frame)}, duplicates={duplicates}, missing={missing_counts}"
        )
    return {
        "row_count": len(frame),
        "player_count": int(frame["Id"].nunique()),
        "team_count": int(frame["Team"].nunique()),
        "duplicate_player_team_count": duplicates,
        "missing_required": missing_counts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KBO 공식 기록실 2026 진행 시즌 snapshot 수집")
    parser.add_argument("--delay", type=float, default=1.0, help="요청 사이 최소 간격(초)")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--as-of", type=date.fromisoformat, default=None, help="YYYY-MM-DD")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.delay < 1.0:
        raise ValueError("KBO 서버 보호를 위해 --delay는 1초 이상이어야 합니다.")
    project_root = Path(__file__).resolve().parents[1]
    output_directory = args.output_dir
    if not output_directory.is_absolute():
        output_directory = project_root / output_directory
    output_directory.mkdir(parents=True, exist_ok=True)
    as_of_date = args.as_of or datetime.now(ZoneInfo("Asia/Seoul")).date()

    crawler = KboCrawler(args.delay)
    started_at = datetime.now(ZoneInfo("Asia/Seoul"))
    try:
        print("robots.txt 확인", flush=True)
        crawler.check_robots()
        print("타자 기록 수집", flush=True)
        batting = merge_endpoint_records(
            [crawler.scrape_endpoint(path, HITTER_STAT_MAP) for path in HITTER_ENDPOINTS]
        )
        print("투수 기록 수집", flush=True)
        pitching = merge_endpoint_records(
            [crawler.scrape_endpoint(path, PITCHER_STAT_MAP) for path in PITCHER_ENDPOINTS]
        )
        records_by_role = {"batting": batting, "pitching": pitching}
        known = historical_profiles(project_root / "data" / "raw")
        new_players = enrich_profiles(crawler, records_by_role, known)

        batting_frame = frame_for_output(batting, HITTER_COLUMNS, as_of_date)
        pitching_frame = frame_for_output(pitching, PITCHER_COLUMNS, as_of_date)
        batting_quality = validate_snapshot(batting_frame, "batting")
        pitching_quality = validate_snapshot(pitching_frame, "pitching")

        batting_path = output_directory / "kbo_batting_stats_season_2026_partial.csv"
        pitching_path = output_directory / "kbo_pitching_stats_season_2026_partial.csv"
        batting_frame.to_csv(batting_path, index=False, encoding="utf-8-sig")
        pitching_frame.to_csv(pitching_path, index=False, encoding="utf-8-sig")

        manifest = {
            "season": SEASON,
            "as_of_date": as_of_date.isoformat(),
            "is_partial": True,
            "source": BASE_URL,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "request_count": crawler.request_count,
            "minimum_request_delay_seconds": args.delay,
            "new_player_profiles_fetched": new_players,
            "batting": {
                "path": batting_path.relative_to(project_root).as_posix(),
                **batting_quality,
            },
            "pitching": {
                "path": pitching_path.relative_to(project_root).as_posix(),
                **pitching_quality,
            },
        }
        report_path = project_root / "reports" / "kbo-2026-snapshot.json"
        report_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
