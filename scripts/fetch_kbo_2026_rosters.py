"""KBO 공식 선수 등록 현황에서 2026 구단별 1군 로스터를 수집한다.

선수 등록 명단은 날짜에 따라 달라지므로 원본 행마다 기준일과 활성 상태를 저장한다.
감독과 코치는 제외하고 투수·포수·내야수·외야수만 수집한다.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse
from zoneinfo import ZoneInfo

import pandas as pd

from fetch_kbo_2026 import BASE_URL, KboCrawler

SEASON = 2026
REGISTER_PATH = "/Player/Register.aspx"
TEAM_CODES = ("SS", "KT", "LG", "HT", "OB", "HH", "NC", "LT", "SK", "WO")
TEAM_NAMES = {
    "SS": "삼성",
    "KT": "KT",
    "LG": "LG",
    "HT": "KIA",
    "OB": "두산",
    "HH": "한화",
    "NC": "NC",
    "LT": "롯데",
    "SK": "SSG",
    "WO": "키움",
}
POSITION_CODES = {"투수": "P", "포수": "C", "내야수": "IF", "외야수": "OF"}
SEARCH_TEAM_FIELD = (
    "ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$hfSearchTeam"
)
CALENDAR_BUTTON = (
    "ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$btnCalendarSelect"
)
OUTPUT_COLUMNS = (
    "Season",
    "AsOfDate",
    "TeamCode",
    "Team",
    "PlayerId",
    "Player",
    "Position",
    "UniformNumber",
    "BatThrow",
    "Born",
    "HtWt",
    "URL",
    "IsActive",
)


@dataclass(slots=True)
class Table:
    headers: list[str] = field(default_factory=list)
    rows: list[list[dict[str, str]]] = field(default_factory=list)


class RosterTableParser(HTMLParser):
    """선수 등록 명단의 tNData 테이블을 셀 텍스트와 링크로 변환한다."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[Table] = []
        self._table: Table | None = None
        self._in_header = False
        self._row: list[dict[str, str]] | None = None
        self._cell: dict[str, str] | None = None
        self._cell_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table" and "tNData" in (attributes.get("class") or "").split():
            self._table = Table()
            return
        if self._table is None:
            return
        if tag == "thead":
            self._in_header = True
        elif tag == "tr":
            self._row = []
        elif tag in {"th", "td"}:
            self._cell = {"text": "", "href": ""}
            self._cell_parts = []
        elif tag == "a" and self._cell is not None:
            self._cell["href"] = attributes.get("href") or ""

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._table is None:
            return
        if tag in {"th", "td"} and self._cell is not None:
            self._cell["text"] = " ".join("".join(self._cell_parts).split())
            if self._row is not None:
                self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                if self._in_header:
                    self._table.headers = [cell["text"] for cell in self._row]
                else:
                    self._table.rows.append(self._row)
            self._row = None
        elif tag == "thead":
            self._in_header = False
        elif tag == "table":
            self.tables.append(self._table)
            self._table = None


def player_id_from_url(url: str) -> int:
    values = parse_qs(urlparse(url).query).get("playerId", [])
    if not values or not values[0].isdigit():
        raise ValueError(f"선수 ID가 없는 KBO URL입니다: {url}")
    return int(values[0])


def displayed_date(page: str) -> date:
    match = re.search(r'id="[^\"]*lblGameDate"[^>]*>(\d{4})\.(\d{2})\.(\d{2})', page)
    if match is None:
        raise ValueError("선수 등록 기준일을 찾을 수 없습니다.")
    return date(*(int(value) for value in match.groups()))


def parse_roster(page: str, team_code: str) -> list[dict[str, Any]]:
    """한 구단 페이지에서 현행 등록 명단만 파싱한다."""

    main_roster = page.split('id="cphContents_cphContents_cphContents_pnlEntryY"', 1)[0]
    parser = RosterTableParser()
    parser.feed(main_roster)
    as_of_date = displayed_date(page)
    records: list[dict[str, Any]] = []
    for table in parser.tables:
        if len(table.headers) < 2:
            continue
        position_label = table.headers[1]
        position_code = POSITION_CODES.get(position_label)
        if position_code is None:
            continue
        for row in table.rows:
            if len(row) < 5 or not row[1]["href"]:
                continue
            source_url = urljoin(BASE_URL, row[1]["href"])
            records.append(
                {
                    "Season": SEASON,
                    "AsOfDate": as_of_date.isoformat(),
                    "TeamCode": team_code,
                    "Team": TEAM_NAMES[team_code],
                    "PlayerId": player_id_from_url(source_url),
                    "Player": row[1]["text"],
                    "Position": position_code,
                    "UniformNumber": row[0]["text"],
                    "BatThrow": row[2]["text"],
                    "Born": row[3]["text"],
                    "HtWt": row[4]["text"],
                    "URL": source_url,
                    "IsActive": True,
                }
            )
    return records


def validate_rosters(frame: pd.DataFrame) -> dict[str, Any]:
    required = [
        "AsOfDate",
        "TeamCode",
        "Team",
        "PlayerId",
        "Player",
        "Position",
        "UniformNumber",
        "BatThrow",
        "Born",
        "URL",
    ]
    missing = {
        column: int(frame[column].isna().sum() + frame[column].astype(str).eq("").sum())
        for column in required
    }
    duplicate_count = int(frame.duplicated(["AsOfDate", "TeamCode", "PlayerId"]).sum())
    invalid_positions = sorted(set(frame["Position"]) - set(POSITION_CODES.values()))
    if (
        frame.empty
        or set(frame["Season"]) != {SEASON}
        or set(frame["TeamCode"]) != set(TEAM_CODES)
        or len(set(frame["AsOfDate"])) != 1
        or duplicate_count
        or invalid_positions
        or any(missing.values())
    ):
        raise ValueError(
            "로스터 검증 실패: "
            f"rows={len(frame)}, teams={frame['TeamCode'].nunique()}, "
            f"duplicates={duplicate_count}, missing={missing}, positions={invalid_positions}"
        )
    team_counts = {
        str(team): int(count)
        for team, count in frame.groupby("Team", sort=True).size().items()
    }
    return {
        "row_count": len(frame),
        "player_count": int(frame["PlayerId"].nunique()),
        "team_count": int(frame["TeamCode"].nunique()),
        "duplicate_team_player_count": duplicate_count,
        "missing_required": missing,
        "rows_by_team": team_counts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KBO 2026 구단별 1군 등록 로스터 수집")
    parser.add_argument("--delay", type=float, default=1.0, help="요청 사이 최소 간격(초)")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
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

    crawler = KboCrawler(args.delay)
    started_at = datetime.now(ZoneInfo("Asia/Seoul"))
    try:
        crawler.check_robots()
        base_page = crawler.request("GET", REGISTER_PATH)
        records: list[dict[str, Any]] = []
        for team_code in TEAM_CODES:
            page = crawler.postback(
                REGISTER_PATH,
                base_page,
                CALENDAR_BUTTON,
                {SEARCH_TEAM_FIELD: team_code},
            )
            team_records = parse_roster(page, team_code)
            records.extend(team_records)
            print(f"{TEAM_NAMES[team_code]}: {len(team_records)}명", flush=True)

        frame = pd.DataFrame(records, columns=OUTPUT_COLUMNS).sort_values(
            ["TeamCode", "Position", "UniformNumber", "PlayerId"]
        )
        quality = validate_rosters(frame)
        output_path = output_directory / "kbo_team_rosters_2026_partial.csv"
        frame.to_csv(output_path, index=False, encoding="utf-8-sig")

        manifest = {
            "season": SEASON,
            "as_of_date": str(frame["AsOfDate"].iloc[0]),
            "is_active_roster_snapshot": True,
            "source": urljoin(BASE_URL, REGISTER_PATH),
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "request_count": crawler.request_count,
            "minimum_request_delay_seconds": args.delay,
            "path": output_path.relative_to(project_root).as_posix(),
            **quality,
        }
        report_path = project_root / "reports" / "kbo-2026-roster-snapshot.json"
        report_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
