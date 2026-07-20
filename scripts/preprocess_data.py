"""KBO 원본 CSV를 DB 적재와 ML 분석에 적합한 형태로 정제한다.

원본 파일은 절대 덮어쓰지 않는다. 컬럼명을 snake_case로 표준화하고, 명확한
도메인 규칙으로만 타입/결측/이닝/신체 정보를 변환한다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from profile_data import innings_to_outs


DEFAULT_BATTING_PATH = Path("data/raw/kbo_batting_stats_season_1982-2025.csv")
DEFAULT_PITCHING_PATH = Path("data/raw/kbo_pitching_stats_season_1982-2025.csv")
DEFAULT_OUTPUT_DIR = Path("data/processed")
DEFAULT_MANIFEST_PATH = Path("reports/preprocessing_manifest.json")

COMMON_RENAME = {
    "Id": "player_id",
    "URL": "source_url",
    "Player": "player_name",
    "Age": "age",
    "Born": "birth_date",
    "Position": "position",
    "BatThrow": "bat_throw",
    "HtWt": "height_weight",
    "Career": "career",
    "Draft": "draft",
    "Season": "season",
    "Team": "team",
}
BATTING_RENAME = {
    **COMMON_RENAME,
    "G": "games",
    "PA": "plate_appearances",
    "AB": "at_bats",
    "R": "runs",
    "H": "hits",
    "2B": "doubles",
    "3B": "triples",
    "HR": "home_runs",
    "TB": "total_bases",
    "RBI": "runs_batted_in",
    "SB": "stolen_bases",
    "CS": "caught_stealing",
    "BB": "walks",
    "HBP": "hit_by_pitch",
    "SO": "strikeouts",
    "GDP": "grounded_into_double_play",
    "SF": "sacrifice_flies",
    "SH": "sacrifice_hits",
    "E": "errors",
    "AVG": "batting_average",
    "SLG": "slugging_percentage",
    "OBP": "on_base_percentage",
    "OPS": "on_base_plus_slugging",
}
PITCHING_RENAME = {
    **COMMON_RENAME,
    "ERA": "earned_run_average",
    "G": "games",
    "CG": "complete_games",
    "SHO": "shutouts",
    "W": "wins",
    "L": "losses",
    "SV": "saves",
    "HLD": "holds",
    "WPCT": "winning_percentage",
    "TBF": "batters_faced",
    "IP": "innings_pitched_display",
    "H": "hits_allowed",
    "HR": "home_runs_allowed",
    "BB": "walks_allowed",
    "HBP": "hit_batters",
    "SO": "strikeouts",
    "R": "runs_allowed",
    "ER": "earned_runs",
}
BATTING_COUNT_COLUMNS = [
    "games", "plate_appearances", "at_bats", "runs", "hits", "doubles",
    "triples", "home_runs", "total_bases", "runs_batted_in", "stolen_bases",
    "caught_stealing", "walks", "hit_by_pitch", "strikeouts",
    "grounded_into_double_play", "sacrifice_flies", "sacrifice_hits", "errors",
]
PITCHING_COUNT_COLUMNS = [
    "games", "complete_games", "shutouts", "wins", "losses", "saves", "holds",
    "batters_faced", "hits_allowed", "home_runs_allowed", "walks_allowed",
    "hit_batters", "strikeouts", "runs_allowed", "earned_runs",
]


def parse_args() -> argparse.Namespace:
    """입출력 경로를 명시적으로 변경할 수 있는 CLI를 구성한다."""

    parser = argparse.ArgumentParser(description="KBO CSV 전처리")
    parser.add_argument("--batting", type=Path, default=DEFAULT_BATTING_PATH)
    parser.add_argument("--pitching", type=Path, default=DEFAULT_PITCHING_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    """전처리 재현성 확인용 SHA-256을 계산한다."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_validate(path: Path, expected_columns: list[str]) -> pd.DataFrame:
    """원본 스키마와 핵심키 무결성을 확인한 뒤 문자열 DataFrame을 반환한다."""

    frame = pd.read_csv(path, dtype="string", keep_default_na=False, encoding="utf-8")
    actual_columns = frame.columns.tolist()
    if actual_columns != expected_columns:
        raise ValueError(
            f"{path} 스키마가 예상과 다릅니다. "
            f"expected={expected_columns}, actual={actual_columns}"
        )
    if frame.duplicated(["Id", "Season", "Team"]).any():
        raise ValueError(f"{path}에 Id/Season/Team 중복키가 있습니다.")
    return frame


def normalize_text_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """문자열의 양끝 공백을 제거하고 빈 문자열을 명시적 결측으로 바꾼다."""

    result = frame.copy()
    for column in result.select_dtypes(include="string").columns:
        result[column] = result[column].str.strip().replace("", pd.NA)
    return result


def add_physical_dimensions(frame: pd.DataFrame) -> pd.DataFrame:
    """'183cm/88kg'를 숫자 키와 몸무게로 분리하되 원문도 보존한다."""

    result = frame.copy()
    extracted = result["height_weight"].str.extract(r"^(\d+)cm/(\d+)kg$")
    result["height_cm"] = pd.to_numeric(extracted[0], errors="coerce").astype("Int64")
    result["weight_kg"] = pd.to_numeric(extracted[1], errors="coerce").astype("Int64")
    return result


def correct_verified_age(frame: pd.DataFrame) -> pd.DataFrame:
    """생년과 시즌으로 교차 검증되는 나이 오기만 고치고 수정 여부를 남긴다."""

    result = frame.copy()
    supplied_age = pd.to_numeric(result["age"], errors="raise").astype("Int64")
    birth_year = pd.to_datetime(result["birth_date"], errors="raise").dt.year.astype("Int64")
    calculated_age = result["season"] - birth_year
    result["age_was_corrected"] = (supplied_age != calculated_age).astype("boolean")
    result["age"] = calculated_age
    return result


def prepare_common(frame: pd.DataFrame, rename_map: dict[str, str]) -> pd.DataFrame:
    """두 데이터셋이 공유하는 이름, 타입, 신체 정보와 나이를 정제한다."""

    result = normalize_text_columns(frame).rename(columns=rename_map)
    result["player_id"] = pd.to_numeric(result["player_id"], errors="raise").astype("Int64")
    result["season"] = pd.to_numeric(result["season"], errors="raise").astype("Int64")
    result["birth_date"] = pd.to_datetime(result["birth_date"], errors="raise")
    result = correct_verified_age(result)
    result = add_physical_dimensions(result)
    return result


def preprocess_batting(frame: pd.DataFrame) -> pd.DataFrame:
    """타자 누적/비율 기록을 올바른 nullable 숫자형으로 변환한다."""

    result = prepare_common(frame, BATTING_RENAME)
    for column in BATTING_COUNT_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="raise").astype("Int64")
    for column in (
        "batting_average", "slugging_percentage", "on_base_percentage",
        "on_base_plus_slugging",
    ):
        result[column] = pd.to_numeric(
            result[column].replace("-", pd.NA), errors="coerce"
        ).astype("Float64")

    if not result.loc[result["at_bats"].eq(0), "batting_average"].isna().all():
        raise ValueError("0타수 행의 타율은 NULL이어야 합니다.")
    return result.sort_values(["season", "player_id", "team"]).reset_index(drop=True)


def preprocess_pitching(frame: pd.DataFrame) -> pd.DataFrame:
    """투수 기록을 변환하고 이닝을 계산에 안전한 아웃 수로 추가한다."""

    result = prepare_common(frame, PITCHING_RENAME)
    for column in PITCHING_COUNT_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="raise").astype("Int64")
    for column in ("earned_run_average", "winning_percentage"):
        result[column] = pd.to_numeric(
            result[column].replace("-", pd.NA), errors="coerce"
        ).astype("Float64")

    innings_outs, invalid_values = innings_to_outs(result["innings_pitched_display"])
    if invalid_values:
        raise ValueError(f"해석할 수 없는 이닝 값이 있습니다: {invalid_values}")
    result["innings_pitched_outs"] = innings_outs.astype("Int64")

    zero_outs = result["innings_pitched_outs"].eq(0)
    if not result.loc[zero_outs, "earned_run_average"].isna().all():
        raise ValueError("0이닝 행의 ERA는 NULL이어야 합니다.")
    return result.sort_values(["season", "player_id", "team"]).reset_index(drop=True)


def atomic_write_csv(frame: pd.DataFrame, output_path: Path) -> None:
    """완성되지 않은 CSV가 남지 않도록 임시 파일 작성 후 원자적으로 교체한다."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    frame.to_csv(temporary_path, index=False, encoding="utf-8")
    temporary_path.replace(output_path)


def write_manifest(
    manifest_path: Path,
    batting_source: Path,
    pitching_source: Path,
    batting_output: Path,
    pitching_output: Path,
    batting: pd.DataFrame,
    pitching: pd.DataFrame,
) -> None:
    """입출력 해시와 적용 규칙을 기록해 전처리 결과를 추적 가능하게 만든다."""

    manifest = {
        "sources": {
            "batting": {"path": str(batting_source), "sha256": file_sha256(batting_source)},
            "pitching": {"path": str(pitching_source), "sha256": file_sha256(pitching_source)},
        },
        "outputs": {
            "batting": {
                "path": str(batting_output),
                "sha256": file_sha256(batting_output),
                "rows": len(batting),
                "columns": len(batting.columns),
            },
            "pitching": {
                "path": str(pitching_output),
                "sha256": file_sha256(pitching_output),
                "rows": len(pitching),
                "columns": len(pitching.columns),
            },
        },
        "rules": [
            "원본 컬럼명을 snake_case 영문 의미명으로 변환",
            "빈 문자열과 '-' 비율값을 NULL로 변환",
            "생년과 시즌이 증명하는 나이 오기 교정 및 age_was_corrected 추가",
            "height_weight에서 height_cm, weight_kg 파생",
            "야구식 IP 혼합 분수를 innings_pitched_outs로 변환",
            "원본 행 삭제 및 통계값 임의 대치 없음",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    """원본 검증부터 정제 파일 및 manifest 저장까지 실행한다."""

    args = parse_args()
    batting_raw = load_and_validate(args.batting, list(BATTING_RENAME))
    pitching_raw = load_and_validate(args.pitching, list(PITCHING_RENAME))
    batting = preprocess_batting(batting_raw)
    pitching = preprocess_pitching(pitching_raw)

    batting_output = args.output_dir / "batting_stats_clean.csv"
    pitching_output = args.output_dir / "pitching_stats_clean.csv"
    atomic_write_csv(batting, batting_output)
    atomic_write_csv(pitching, pitching_output)
    write_manifest(
        args.manifest,
        args.batting,
        args.pitching,
        batting_output,
        pitching_output,
        batting,
        pitching,
    )
    print(f"타격 데이터 저장 완료: {batting_output} ({len(batting):,}행)")
    print(f"투구 데이터 저장 완료: {pitching_output} ({len(pitching):,}행)")


if __name__ == "__main__":
    main()
