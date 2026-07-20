"""정제 데이터가 MySQL 초기 스키마의 타입과 제약을 만족하는지 검증한다.

MySQL 서버 없이도 데이터 기반 설계 오류를 조기에 발견하기 위한 도구다.
DDL 문법 자체와 migration은 4단계에서 실제 MySQL 테스트 컨테이너로 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


BATTING_PATH = Path("data/processed/batting_stats_clean.csv")
PITCHING_PATH = Path("data/processed/pitching_stats_clean.csv")
OUTPUT_PATH = Path("reports/db_design_validation.json")
EXPECTED_TEAMS = {
    "KIA", "KT", "LG", "MBC", "NC", "OB", "SK", "SSG", "넥센", "두산",
    "롯데", "빙그레", "삼미", "삼성", "쌍방울", "우리", "청보", "키움",
    "태평양", "한화", "해태", "현대", "히어로즈",
}


def require(condition: bool, message: str) -> None:
    """스키마 전제와 다른 데이터가 있으면 원인을 분명하게 표시한다."""

    if not condition:
        raise ValueError(message)


def validate_common(frame: pd.DataFrame, dataset_name: str) -> None:
    """공통 PK, 문자열 길이와 프로필 도메인을 검증한다."""

    require(
        not frame.duplicated(["player_id", "season", "team"]).any(),
        f"{dataset_name}: 시즌 기록 자연키 중복",
    )
    require(frame["player_id"].between(0, 4_294_967_295).all(), "player_id INT 범위 초과")
    require(frame["season"].between(1982, 2200).all(), "season CHECK 범위 위반")
    require(frame["player_name"].str.len().max() <= 100, "player_name 길이 초과")
    require(frame["team"].str.len().max() <= 30, "team_name 길이 초과")
    require(set(frame["team"]) <= EXPECTED_TEAMS, "seed에 없는 팀 발견")
    require(frame["source_url"].str.len().max() <= 500, "source_url 길이 초과")
    require(frame["draft"].fillna("").str.len().max() <= 255, "draft 길이 초과")
    require(
        frame["bat_throw"].str.fullmatch(r"[LRS]/[LR]").all(),
        "bat_throw 도메인 위반",
    )

    height = frame["height_cm"].dropna()
    weight = frame["weight_kg"].dropna()
    require(height.between(140, 230).all(), "height_cm CHECK 범위 위반")
    require(weight.between(40, 180).all(), "weight_kg CHECK 범위 위반")


def validate_batting(frame: pd.DataFrame) -> None:
    """타격 테이블의 정수/비율 및 야구 도메인 제약을 검증한다."""

    validate_common(frame, "batting")
    count_columns = [
        "games", "plate_appearances", "at_bats", "runs", "hits", "doubles",
        "triples", "home_runs", "total_bases", "runs_batted_in", "stolen_bases",
        "caught_stealing", "walks", "hit_by_pitch", "strikeouts",
        "grounded_into_double_play", "sacrifice_flies", "sacrifice_hits", "errors",
    ]
    require((frame[count_columns] >= 0).all().all(), "타격 음수 누적 기록")
    require((frame[count_columns] <= 65_535).all().all(), "타격 SMALLINT 범위 초과")
    require((frame["hits"] <= frame["at_bats"]).all(), "H > AB")
    require((frame["plate_appearances"] >= frame["at_bats"]).all(), "PA < AB")
    require((frame["home_runs"] <= frame["hits"]).all(), "HR > H")
    require(
        (
            frame["doubles"] + frame["triples"] + frame["home_runs"]
            <= frame["hits"]
        ).all(),
        "2B + 3B + HR > H",
    )
    require(frame["position"].str.len().max() <= 5, "position_code 길이 초과")

    for column, upper in {
        "batting_average": 1,
        "slugging_percentage": 4,
        "on_base_percentage": 1,
        "on_base_plus_slugging": 5,
    }.items():
        values = frame[column].dropna()
        require(values.between(0, upper).all(), f"{column} CHECK 범위 위반")

    zero_at_bats = frame["at_bats"].eq(0)
    rate_columns = [
        "batting_average", "slugging_percentage", "on_base_percentage",
        "on_base_plus_slugging",
    ]
    require(frame.loc[zero_at_bats, rate_columns].isna().all().all(), "0타수 비율값 존재")


def validate_pitching(frame: pd.DataFrame) -> None:
    """투구 테이블의 정수/비율 및 야구 도메인 제약을 검증한다."""

    validate_common(frame, "pitching")
    count_columns = [
        "games", "complete_games", "shutouts", "wins", "losses", "saves", "holds",
        "batters_faced", "innings_pitched_outs", "hits_allowed", "home_runs_allowed",
        "walks_allowed", "hit_batters", "strikeouts", "runs_allowed", "earned_runs",
    ]
    require((frame[count_columns] >= 0).all().all(), "투구 음수 누적 기록")
    require((frame[count_columns] <= 65_535).all().all(), "투구 SMALLINT 범위 초과")
    require((frame["earned_runs"] <= frame["runs_allowed"]).all(), "ER > R")
    require((frame["complete_games"] <= frame["games"]).all(), "CG > G")
    require((frame["shutouts"] <= frame["complete_games"]).all(), "SHO > CG")

    era = frame["earned_run_average"].dropna()
    wpct = frame["winning_percentage"].dropna()
    require((era >= 0).all(), "ERA 음수")
    require(wpct.between(0, 1).all(), "WPCT CHECK 범위 위반")
    require(
        frame.loc[frame["innings_pitched_outs"].eq(0), "earned_run_average"].isna().all(),
        "0아웃 ERA 존재",
    )
    no_decision = (frame["wins"] + frame["losses"]).eq(0)
    require(frame.loc[no_decision, "winning_percentage"].isna().all(), "무승패 WPCT 존재")


def validate_player_identity(batting: pd.DataFrame, pitching: pd.DataFrame) -> int:
    """한 player_id가 서로 다른 이름/생년을 가리키지 않는지 확인한다."""

    identity = pd.concat(
        [
            batting[["player_id", "player_name", "birth_date"]],
            pitching[["player_id", "player_name", "birth_date"]],
        ],
        ignore_index=True,
    ).drop_duplicates()
    conflicts = identity.groupby("player_id").size()
    require((conflicts == 1).all(), "파일 간 player_id 신원 충돌")
    return identity["player_id"].nunique()


def main() -> None:
    """모든 설계 제약을 검사하고 예상 테이블 cardinality를 기록한다."""

    batting = pd.read_csv(BATTING_PATH)
    pitching = pd.read_csv(PITCHING_PATH)
    validate_batting(batting)
    validate_pitching(pitching)
    player_count = validate_player_identity(batting, pitching)

    result = {
        "status": "passed",
        "expected_cardinality": {
            "players": player_count,
            "player_source_profiles": (
                batting["player_id"].nunique() + pitching["player_id"].nunique()
            ),
            "teams": len(EXPECTED_TEAMS),
            "batting_season_stats": len(batting),
            "pitching_season_stats": len(pitching),
        },
        "validated": [
            "natural_key_uniqueness",
            "foreign_key_source_domains",
            "mysql_integer_ranges",
            "varchar_lengths",
            "profile_domains",
            "batting_check_constraints",
            "pitching_check_constraints",
            "cross_file_player_identity",
        ],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"DB 설계 데이터 검증 통과: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
