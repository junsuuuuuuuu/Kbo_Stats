"""KBO 공식 팀 순위에서 2026 정규시즌 전적 스냅샷을 수집한다."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import pandas as pd

from fetch_kbo_2026 import BASE_URL, KboCrawler
from fetch_kbo_2026_rosters import TEAM_CODES, TEAM_NAMES

SEASON = 2026
STANDINGS_PATH = "/Record/TeamRank/TeamRank.aspx"
NAME_TO_CODE = {name: code for code, name in TEAM_NAMES.items()}
OUTPUT_COLUMNS = (
    "Season", "AsOfDate", "TeamCode", "Team", "Rank", "Games", "Wins", "Losses",
    "Draws", "WinningPercentage", "GamesBehind", "RecentTen", "Streak", "Home", "Away",
    "SourceURL",
)


@dataclass(slots=True)
class HtmlTable:
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


class StandingsTableParser(HTMLParser):
    """HTML 표를 텍스트 행으로 변환한다."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[HtmlTable] = []
        self._table: HtmlTable | None = None
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None
        self._header_row = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = HtmlTable()
        elif self._table is not None and tag == "tr":
            self._row = []
            self._header_row = False
        elif self._row is not None and tag in {"th", "td"}:
            self._cell_parts = []
            self._header_row = self._header_row or tag == "th"

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._cell_parts is not None:
            if self._row is not None:
                self._row.append(" ".join("".join(self._cell_parts).split()))
            self._cell_parts = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._header_row:
                self._table.headers = self._row
            elif self._row:
                self._table.rows.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def parse_standings(page: str, *, as_of_date: str) -> list[dict[str, Any]]:
    parser = StandingsTableParser()
    parser.feed(page)
    table = next(
        (
            item for item in parser.tables
            if item.headers[:6] == ["순위", "팀명", "경기", "승", "패", "무"]
        ),
        None,
    )
    if table is None:
        raise ValueError("KBO 팀 순위 표를 찾을 수 없습니다.")

    records: list[dict[str, Any]] = []
    for row in table.rows:
        if len(row) < 12 or row[1] not in NAME_TO_CODE:
            continue
        records.append(
            {
                "Season": SEASON,
                "AsOfDate": as_of_date,
                "TeamCode": NAME_TO_CODE[row[1]],
                "Team": row[1],
                "Rank": int(row[0]),
                "Games": int(row[2]),
                "Wins": int(row[3]),
                "Losses": int(row[4]),
                "Draws": int(row[5]),
                "WinningPercentage": float(row[6]),
                "GamesBehind": float(row[7]),
                "RecentTen": row[8],
                "Streak": row[9],
                "Home": row[10],
                "Away": row[11],
                "SourceURL": urljoin(BASE_URL, STANDINGS_PATH),
            }
        )
    return records


def validate_standings(frame: pd.DataFrame) -> dict[str, Any]:
    if len(frame) != 10 or set(frame["TeamCode"]) != set(TEAM_CODES):
        raise ValueError(f"전적 검증 실패: rows={len(frame)}, teams={sorted(frame['TeamCode'])}")
    if set(frame["Rank"]) != set(range(1, 11)):
        raise ValueError("전적 검증 실패: 순위가 1~10의 순열이 아닙니다.")
    if not (frame["Games"] == frame["Wins"] + frame["Losses"] + frame["Draws"]).all():
        raise ValueError("전적 검증 실패: 경기 수와 승·패·무 합계가 다릅니다.")
    if not frame["WinningPercentage"].between(0, 1).all():
        raise ValueError("전적 검증 실패: 승률 범위를 벗어났습니다.")
    return {
        "team_count": 10,
        "leader": str(frame.sort_values("Rank").iloc[0]["Team"]),
        "total_games": int(frame["Games"].sum() // 2),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KBO 2026 정규시즌 팀 전적 수집")
    parser.add_argument("--delay", type=float, default=1.0)
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

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    crawler = KboCrawler(args.delay)
    try:
        crawler.check_robots()
        page = crawler.request("GET", STANDINGS_PATH)
        frame = pd.DataFrame(
            parse_standings(page, as_of_date=now.date().isoformat()),
            columns=OUTPUT_COLUMNS,
        ).sort_values("Rank")
        quality = validate_standings(frame)
        output_path = output_directory / "kbo_team_standings_2026_partial.csv"
        frame.to_csv(output_path, index=False, encoding="utf-8-sig")
        manifest = {
            "season": SEASON,
            "as_of_date": now.date().isoformat(),
            "source": urljoin(BASE_URL, STANDINGS_PATH),
            "request_count": crawler.request_count,
            "path": output_path.relative_to(project_root).as_posix(),
            **quality,
        }
        report_path = project_root / "reports" / "kbo-2026-standings-snapshot.json"
        report_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
