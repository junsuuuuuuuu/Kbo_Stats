"""수집한 2026 구단별 1군 등록 로스터를 MySQL에 적재한다."""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.player import Player
from app.models.roster import TeamRoster
from app.models.team import Team

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROSTER_PATH = PROJECT_ROOT / "data" / "raw" / "kbo_team_rosters_2026_partial.csv"
EXPECTED_COLUMNS = [
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
]


def parse_sides(value: str) -> tuple[str, str]:
    """KBO 한글 투타 표기를 영문 bat/throw side로 변환한다."""

    match = re.fullmatch(r"(우|좌)(?:투|언)(우|좌|양)타", value)
    if match is None:
        raise ValueError(f"해석할 수 없는 투타유형입니다: {value}")
    throw_side = {"우": "R", "좌": "L"}[match.group(1)]
    bat_side = {"우": "R", "좌": "L", "양": "S"}[match.group(2)]
    return bat_side, throw_side


def parse_physical(value: str) -> tuple[int | None, int | None]:
    """KBO 체격 표기에서 허용 범위의 신장·체중만 반환한다."""

    match = re.fullmatch(r"(\d+)cm,\s*(\d+)kg", value)
    if match is None:
        return None, None
    height, weight = (int(part) for part in match.groups())
    return (
        height if 140 <= height <= 230 else None,
        weight if 40 <= weight <= 180 else None,
    )


def parse_active(value: str) -> bool:
    """CSV boolean을 엄격하게 변환한다."""

    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"IsActive는 True 또는 False여야 합니다: {value}")
    return normalized == "true"


def load_rows(path: Path = ROSTER_PATH) -> list[dict[str, str]]:
    """BOM을 허용해 로스터 CSV를 읽고 스키마를 검증한다."""

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError(
                f"로스터 CSV 스키마가 다릅니다: expected={EXPECTED_COLUMNS}, "
                f"actual={reader.fieldnames}"
            )
        rows = list(reader)
    if not rows:
        raise ValueError("로스터 CSV가 비어 있습니다.")
    return rows


def build_records(session: Session, rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """팀·선수 신원을 대조하고 DB insert record를 만든다."""

    teams = {team.team_name: team for team in session.scalars(select(Team)).all()}
    player_ids = {int(row["PlayerId"]) for row in rows}
    players = {
        player.player_id: player
        for player in session.scalars(select(Player).where(Player.player_id.in_(player_ids))).all()
    }
    missing_players = player_ids - players.keys()
    if missing_players:
        raise ValueError(f"players 테이블에 없는 KBO ID입니다: {sorted(missing_players)}")

    records: list[dict[str, object]] = []
    for row in rows:
        player_id = int(row["PlayerId"])
        player = players[player_id]
        team = teams.get(row["Team"])
        if team is None:
            raise ValueError(f"teams 테이블에 없는 팀입니다: {row['Team']}")
        born = date.fromisoformat(row["Born"])
        if player.player_name != row["Player"] or player.birth_date != born:
            raise ValueError(f"player_id={player_id}의 로스터 신원이 DB와 충돌합니다.")
        bat_side, throw_side = parse_sides(row["BatThrow"])
        height_cm, weight_kg = parse_physical(row["HtWt"])
        records.append(
            {
                "season": int(row["Season"]),
                "as_of_date": date.fromisoformat(row["AsOfDate"]),
                "team_id": team.team_id,
                "team_code": row["TeamCode"],
                "player_id": player_id,
                "position_code": row["Position"],
                "uniform_number": row["UniformNumber"],
                "bat_side": bat_side,
                "throw_side": throw_side,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "source_url": row["URL"],
                "is_active": parse_active(row["IsActive"]),
            }
        )
    return records


def import_rosters(session: Session, rows: list[dict[str, str]]) -> int:
    """검증된 동일 날짜 snapshot을 원자적으로 교체한다."""

    records = build_records(session, rows)
    seasons = {record["season"] for record in records}
    dates = {record["as_of_date"] for record in records}
    teams = {record["team_code"] for record in records}
    if len(seasons) != 1 or len(dates) != 1 or len(teams) != 10:
        raise ValueError("로스터 snapshot은 한 시즌·한 기준일·10개 구단이어야 합니다.")
    season = next(iter(seasons))
    as_of_date = next(iter(dates))
    try:
        session.execute(
            delete(TeamRoster).where(
                TeamRoster.season == season,
                TeamRoster.as_of_date == as_of_date,
            )
        )
        session.execute(TeamRoster.__table__.insert(), records)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return len(records)


def main() -> None:
    rows = load_rows()
    with SessionLocal() as session:
        count = import_rosters(session, rows)
    print(f"2026 구단 로스터 적재 완료: {count}명")


if __name__ == "__main__":
    main()
