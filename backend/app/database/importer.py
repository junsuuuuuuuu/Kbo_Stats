"""정제 CSV를 핵심 MySQL 테이블에 재현 가능하게 적재한다."""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.models.import_batch import DataImportBatch
from app.models.player import Player, PlayerSourceProfile
from app.models.stats import BattingSeasonStat, PitchingSeasonStat
from app.models.team import Team

ROLE_BATTING = "BATTING"
ROLE_PITCHING = "PITCHING"
BATCH_SIZE = 1_000


class AlreadyImportedError(RuntimeError):
    """동일한 원본 dataset/hash의 중복 적재 요청."""


def utc_now_naive() -> datetime:
    """MySQL DATETIME에 저장할 UTC 기준 naive datetime을 반환한다."""

    return datetime.now(UTC).replace(tzinfo=None)


def file_sha256(path: Path) -> str:
    """처리 파일의 무결성 메타데이터를 계산한다."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    """UTF-8 정제 CSV를 헤더 기반 dictionary 행으로 읽는다."""

    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def chunks(records: Sequence[dict[str, Any]], size: int = BATCH_SIZE):
    """DB parameter 제한과 메모리 급증을 피하도록 record를 나눈다."""

    for start in range(0, len(records), size):
        yield records[start : start + size]


def nullable_int(value: str) -> int | None:
    """정제 CSV의 빈 숫자를 NULL로 변환한다."""

    return int(value) if value else None


def nullable_decimal(value: str) -> Decimal | None:
    """비율 지표의 10진 정밀도를 보존한다."""

    return Decimal(value) if value else None


def normalize_search_name(player_name: str) -> str:
    """PlayerService 검색 정규화 규칙과 동일한 값을 생성한다."""

    return "".join(player_name.split()).lower()


def build_player_records(rows: Iterable[dict[str, str]]) -> dict[int, dict[str, Any]]:
    """반복 시즌 행에서 공통 선수 신원을 하나로 축약하고 충돌을 차단한다."""

    players: dict[int, dict[str, Any]] = {}
    for row in rows:
        player_id = int(row["player_id"])
        identity = {
            "player_id": player_id,
            "player_name": row["player_name"],
            "search_name": normalize_search_name(row["player_name"]),
            "birth_date": date.fromisoformat(row["birth_date"]),
        }
        existing = players.get(player_id)
        if existing is not None and existing != identity:
            raise ValueError(f"player_id={player_id}의 파일 내 신원이 충돌합니다.")
        players[player_id] = identity
    return players


def build_profile_records(
    rows: Iterable[dict[str, str]], role: str
) -> dict[tuple[int, str], dict[str, Any]]:
    """역할 내 불변 프로필을 축약하고 결측 신체 정보는 비결측 값으로 보완한다."""

    profiles: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        player_id = int(row["player_id"])
        bat_side, throw_side = row["bat_throw"].split("/", maxsplit=1)
        key = (player_id, role)
        candidate = {
            "player_id": player_id,
            "profile_role": role,
            "source_url": row["source_url"],
            "bat_side": bat_side,
            "throw_side": throw_side,
            "height_cm": nullable_int(row["height_cm"]),
            "weight_kg": nullable_int(row["weight_kg"]),
            "career": row["career"] or None,
            "draft": row["draft"] or None,
        }
        existing = profiles.get(key)
        if existing is None:
            profiles[key] = candidate
            continue

        for stable_field in ("source_url", "bat_side", "throw_side", "career", "draft"):
            current_value = existing[stable_field]
            candidate_value = candidate[stable_field]
            if current_value and candidate_value and current_value != candidate_value:
                raise ValueError(
                    f"player_id={player_id}, role={role}의 {stable_field} 값이 충돌합니다."
                )
            if current_value is None:
                existing[stable_field] = candidate_value
        for physical_field in ("height_cm", "weight_kg"):
            if existing[physical_field] is None:
                existing[physical_field] = candidate[physical_field]
    return profiles


def build_batting_stats(
    rows: Iterable[dict[str, str]], team_ids: dict[str, int], import_batch_id: int
) -> list[dict[str, Any]]:
    """타자 정제 행을 ORM 테이블 컬럼 record로 변환한다."""

    count_columns = [
        "games",
        "plate_appearances",
        "at_bats",
        "runs",
        "hits",
        "doubles",
        "triples",
        "home_runs",
        "total_bases",
        "runs_batted_in",
        "stolen_bases",
        "caught_stealing",
        "walks",
        "hit_by_pitch",
        "strikeouts",
        "grounded_into_double_play",
        "sacrifice_flies",
        "sacrifice_hits",
        "errors",
    ]
    rate_columns = [
        "batting_average",
        "slugging_percentage",
        "on_base_percentage",
        "on_base_plus_slugging",
    ]
    result: list[dict[str, Any]] = []
    for row in rows:
        record: dict[str, Any] = {
            "player_id": int(row["player_id"]),
            "team_id": team_ids[row["team"]],
            "import_batch_id": import_batch_id,
            "season": int(row["season"]),
            "position_code": row["position"],
        }
        record.update({column: int(row[column]) for column in count_columns})
        record.update({column: nullable_decimal(row[column]) for column in rate_columns})
        result.append(record)
    return result


def build_pitching_stats(
    rows: Iterable[dict[str, str]], team_ids: dict[str, int], import_batch_id: int
) -> list[dict[str, Any]]:
    """투수 정제 행을 ORM 테이블 컬럼 record로 변환한다."""

    count_columns = [
        "games",
        "complete_games",
        "shutouts",
        "wins",
        "losses",
        "saves",
        "holds",
        "batters_faced",
        "innings_pitched_outs",
        "hits_allowed",
        "home_runs_allowed",
        "walks_allowed",
        "hit_batters",
        "strikeouts",
        "runs_allowed",
        "earned_runs",
    ]
    result: list[dict[str, Any]] = []
    for row in rows:
        record: dict[str, Any] = {
            "player_id": int(row["player_id"]),
            "team_id": team_ids[row["team"]],
            "import_batch_id": import_batch_id,
            "season": int(row["season"]),
            "earned_run_average": nullable_decimal(row["earned_run_average"]),
            "winning_percentage": nullable_decimal(row["winning_percentage"]),
        }
        record.update({column: int(row[column]) for column in count_columns})
        result.append(record)
    return result


def get_team_ids(session: Session, rows: Iterable[dict[str, str]]) -> dict[str, int]:
    """CSV 팀 집합이 migration seed에 모두 존재하는지 검증한다."""

    requested_names = {row["team"] for row in rows}
    teams = session.execute(select(Team.team_id, Team.team_name)).all()
    team_ids = {team_name: team_id for team_id, team_name in teams}
    missing = requested_names - team_ids.keys()
    if missing:
        raise ValueError(f"teams seed에 없는 값이 있습니다: {sorted(missing)}")
    return team_ids


def insert_new_players(session: Session, players: dict[int, dict[str, Any]]) -> None:
    """기존 신원과 충돌을 검사한 뒤 신규 선수만 insert한다."""

    existing_players = session.scalars(
        select(Player).where(Player.player_id.in_(players.keys()))
    ).all()
    existing_ids: set[int] = set()
    for existing in existing_players:
        expected = players[existing.player_id]
        if (
            existing.player_name != expected["player_name"]
            or existing.birth_date != expected["birth_date"]
        ):
            raise ValueError(f"player_id={existing.player_id}의 DB 신원이 충돌합니다.")
        existing_ids.add(existing.player_id)

    new_players = [record for player_id, record in players.items() if player_id not in existing_ids]
    for batch in chunks(new_players):
        session.execute(insert(Player), batch)


def mysql_upsert(
    session: Session, model: Any, records: list[dict[str, Any]], keys: set[str]
) -> None:
    """자연키는 유지하고 나머지 적재 필드를 batch 단위로 갱신한다."""

    if not records:
        return
    table = model.__table__
    for batch in chunks(records):
        statement = mysql_insert(table).values(batch)
        updates = {column: statement.inserted[column] for column in batch[0] if column not in keys}
        session.execute(statement.on_duplicate_key_update(**updates))


def create_batch(
    session: Session,
    *,
    dataset_type: str,
    source_file_name: str,
    source_sha256: str,
    row_count: int,
    quality_report: dict[str, Any],
) -> int:
    """동일 원본 중복을 차단하고 RUNNING batch를 독립 transaction으로 남긴다."""

    existing = session.scalar(
        select(DataImportBatch).where(
            DataImportBatch.dataset_type == dataset_type,
            DataImportBatch.source_sha256 == source_sha256,
        )
    )
    if existing is not None:
        raise AlreadyImportedError(
            f"이미 적재한 원본입니다: dataset={dataset_type}, batch={existing.import_batch_id}"
        )

    batch = DataImportBatch(
        dataset_type=dataset_type,
        source_file_name=source_file_name,
        source_sha256=source_sha256,
        source_row_count=row_count,
        status="RUNNING",
        quality_report=quality_report,
        started_at=utc_now_naive(),
    )
    session.add(batch)
    session.commit()
    return batch.import_batch_id


def import_dataset(
    session: Session,
    *,
    dataset_type: str,
    cleaned_path: Path,
    raw_file_name: str,
    raw_sha256: str,
) -> int:
    """한 역할의 프로필/시즌 기록을 transaction으로 적재하고 batch 상태를 갱신한다."""

    rows = load_csv(cleaned_path)
    quality_report = {
        "cleaned_file": str(cleaned_path),
        "cleaned_sha256": file_sha256(cleaned_path),
        "corrected_age_rows": sum(row["age_was_corrected"] == "True" for row in rows),
    }
    import_batch_id = create_batch(
        session,
        dataset_type=dataset_type,
        source_file_name=raw_file_name,
        source_sha256=raw_sha256,
        row_count=len(rows),
        quality_report=quality_report,
    )

    try:
        team_ids = get_team_ids(session, rows)
        players = build_player_records(rows)
        profiles = list(build_profile_records(rows, dataset_type).values())
        insert_new_players(session, players)
        mysql_upsert(
            session,
            PlayerSourceProfile,
            profiles,
            keys={"player_id", "profile_role"},
        )

        if dataset_type == ROLE_BATTING:
            stats = build_batting_stats(rows, team_ids, import_batch_id)
            mysql_upsert(
                session,
                BattingSeasonStat,
                stats,
                keys={"player_id", "season", "team_id"},
            )
        elif dataset_type == ROLE_PITCHING:
            stats = build_pitching_stats(rows, team_ids, import_batch_id)
            mysql_upsert(
                session,
                PitchingSeasonStat,
                stats,
                keys={"player_id", "season", "team_id"},
            )
        else:
            raise ValueError(f"지원하지 않는 dataset_type입니다: {dataset_type}")

        batch = session.get(DataImportBatch, import_batch_id)
        if batch is None:
            raise RuntimeError("적재 batch를 다시 찾을 수 없습니다.")
        batch.imported_row_count = len(stats)
        batch.status = "SUCCEEDED"
        batch.finished_at = utc_now_naive()
        session.commit()
        return import_batch_id
    except Exception:
        session.rollback()
        failed_batch = session.get(DataImportBatch, import_batch_id)
        if failed_batch is not None:
            failed_batch.status = "FAILED"
            failed_batch.finished_at = utc_now_naive()
            session.commit()
        raise
