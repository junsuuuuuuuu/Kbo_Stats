"""수집한 2026 팀 전적 스냅샷을 MySQL에 적재한다."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.standing import TeamStanding
from app.models.team import Team

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STANDINGS_PATH = PROJECT_ROOT / "data" / "raw" / "kbo_team_standings_2026_partial.csv"
EXPECTED_COLUMNS = [
    "Season",
    "AsOfDate",
    "TeamCode",
    "Team",
    "Rank",
    "Games",
    "Wins",
    "Losses",
    "Draws",
    "WinningPercentage",
    "GamesBehind",
    "RecentTen",
    "Streak",
    "Home",
    "Away",
    "SourceURL",
]


def load_rows(path: Path = STANDINGS_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError(f"전적 CSV 스키마가 다릅니다: {reader.fieldnames}")
        rows = list(reader)
    if len(rows) != 10:
        raise ValueError(f"전적 CSV는 10개 구단이어야 합니다: {len(rows)}")
    return rows


def build_records(session: Session, rows: list[dict[str, str]]) -> list[dict[str, object]]:
    teams = {team.team_name: team for team in session.scalars(select(Team)).all()}
    records: list[dict[str, object]] = []
    for row in rows:
        team = teams.get(row["Team"])
        if team is None:
            raise ValueError(f"teams 테이블에 없는 팀입니다: {row['Team']}")
        records.append(
            {
                "season": int(row["Season"]),
                "as_of_date": date.fromisoformat(row["AsOfDate"]),
                "team_id": team.team_id,
                "team_code": row["TeamCode"],
                "ranking": int(row["Rank"]),
                "games": int(row["Games"]),
                "wins": int(row["Wins"]),
                "losses": int(row["Losses"]),
                "draws": int(row["Draws"]),
                "winning_percentage": Decimal(row["WinningPercentage"]),
                "games_behind": Decimal(row["GamesBehind"]),
                "recent_ten": row["RecentTen"],
                "streak": row["Streak"],
                "home_record": row["Home"],
                "away_record": row["Away"],
                "source_url": row["SourceURL"],
            }
        )
    return records


def import_standings(session: Session, rows: list[dict[str, str]]) -> int:
    records = build_records(session, rows)
    season = records[0]["season"]
    as_of_date = records[0]["as_of_date"]
    if any(row["season"] != season or row["as_of_date"] != as_of_date for row in records):
        raise ValueError("전적 snapshot은 한 시즌·한 기준일이어야 합니다.")
    try:
        session.execute(
            delete(TeamStanding).where(
                TeamStanding.season == season,
                TeamStanding.as_of_date == as_of_date,
            )
        )
        session.execute(TeamStanding.__table__.insert(), records)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return len(records)


def main() -> None:
    with SessionLocal() as session:
        count = import_standings(session, load_rows())
    print(f"2026 구단 전적 적재 완료: {count}개 구단")


if __name__ == "__main__":
    main()
