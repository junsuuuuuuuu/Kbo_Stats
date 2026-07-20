"""KBO 원본 CSV의 구조와 품질을 재현 가능하게 점검한다.

이 스크립트는 원본을 수정하지 않으며, 분석 결과만 JSON으로 저장한다.
DB 스키마와 정제 규칙을 데이터에 근거해 결정하기 위한 2단계 도구다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_BATTING_PATH = Path("data/raw/kbo_batting_stats_season_1982-2025.csv")
DEFAULT_PITCHING_PATH = Path("data/raw/kbo_pitching_stats_season_1982-2025.csv")
DEFAULT_OUTPUT_PATH = Path("reports/data_profile.json")
IDENTITY_COLUMNS = [
    "Id",
    "URL",
    "Player",
    "Age",
    "Born",
    "Position",
    "BatThrow",
    "HtWt",
    "Career",
    "Draft",
]
KEY_COLUMNS = ["Id", "Season", "Team"]


def parse_args() -> argparse.Namespace:
    """CLI 인자를 파싱한다."""

    parser = argparse.ArgumentParser(description="KBO CSV 데이터 품질 분석")
    parser.add_argument("--batting", type=Path, default=DEFAULT_BATTING_PATH)
    parser.add_argument("--pitching", type=Path, default=DEFAULT_PITCHING_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def sha256(path: Path) -> str:
    """메모리를 과도하게 사용하지 않고 파일 해시를 계산한다."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_raw_csv(path: Path) -> pd.DataFrame:
    """원문 표현과 placeholder를 보존하기 위해 모든 컬럼을 문자열로 읽는다."""

    return pd.read_csv(path, dtype="string", keep_default_na=False, encoding="utf-8")


def to_number(series: pd.Series) -> pd.Series:
    """공백과 '-'를 결측으로 간주해 수치형으로 변환한다."""

    cleaned = series.str.strip().replace({"": pd.NA, "-": pd.NA})
    return pd.to_numeric(cleaned, errors="coerce")


def innings_to_outs(series: pd.Series) -> tuple[pd.Series, list[str]]:
    """'10 1/3', '2/3', '10.1' 형태의 이닝을 아웃 수로 변환한다.

    현재 원본은 혼합 분수를 사용하지만, 추후 수집 형식이 소수 표기로 바뀌어도
    같은 도메인 값으로 처리할 수 있도록 두 표기를 모두 지원한다.
    """

    outs: list[float] = []
    invalid: set[str] = set()

    for raw_value in series:
        value = str(raw_value).strip()
        if value in {"", "-", "<NA>"}:
            outs.append(np.nan)
            continue

        mixed_fraction = re.fullmatch(r"(?:(\d+) )?([12])/3", value)
        if mixed_fraction:
            whole = int(mixed_fraction.group(1) or 0)
            numerator = int(mixed_fraction.group(2))
            outs.append(whole * 3 + numerator)
            continue

        decimal_notation = re.fullmatch(r"(\d+)(?:\.([012]))?", value)
        if not decimal_notation:
            invalid.add(value)
            outs.append(np.nan)
            continue
        whole = int(decimal_notation.group(1))
        remainder_outs = int(decimal_notation.group(2) or 0)
        outs.append(whole * 3 + remainder_outs)

    return pd.Series(outs, index=series.index, dtype="Float64"), sorted(invalid)


def numeric_summary(frame: pd.DataFrame, columns: list[str]) -> dict[str, Any]:
    """존재하는 수치 후보 컬럼의 변환 실패와 범위를 요약한다."""

    result: dict[str, Any] = {}
    for column in columns:
        if column not in frame:
            continue
        raw = frame[column].str.strip()
        numeric = to_number(raw)
        non_placeholder = ~raw.isin(["", "-"])
        result[column] = {
            "missing_or_placeholder": int((~non_placeholder).sum()),
            "parse_failures": int((non_placeholder & numeric.isna()).sum()),
            "min": None if numeric.dropna().empty else float(numeric.min()),
            "max": None if numeric.dropna().empty else float(numeric.max()),
            "negative_count": int((numeric < 0).sum()),
        }
    return result


def identity_conflicts(frame: pd.DataFrame) -> dict[str, Any]:
    """같은 선수 ID에 변하지 않아야 할 값이 여러 개인지 확인한다."""

    stable_columns = ["Player", "Born", "BatThrow"]
    conflicts: dict[str, Any] = {}
    for column in stable_columns:
        counts = frame.groupby("Id")[column].nunique(dropna=False)
        conflict_ids = counts[counts > 1].index.astype(str).tolist()
        conflicts[column] = {
            "player_count": len(conflict_ids),
            "sample_ids": conflict_ids[:10],
        }
    return conflicts


def common_profile(frame: pd.DataFrame, path: Path) -> dict[str, Any]:
    """타자와 투수 파일에 공통인 구조/무결성 지표를 만든다."""

    stripped = frame.apply(lambda column: column.str.strip())
    blank_counts = (stripped == "").sum()
    placeholder_counts = (stripped == "-").sum()
    season = to_number(frame["Season"])
    age = to_number(frame["Age"])
    born_year = pd.to_datetime(frame["Born"], errors="coerce").dt.year
    expected_age = season - born_year
    age_mismatch = age.notna() & expected_age.notna() & (age != expected_age)

    same_name_ids = frame.groupby("Player")["Id"].nunique()
    duplicated_names = same_name_ids[same_name_ids > 1].sort_values(ascending=False)
    suspicious_age = frame.loc[
        age_mismatch | ~age.between(15, 50),
        ["Id", "Player", "Age", "Born", "Season", "Team"],
    ]

    return {
        "file": str(path),
        "sha256": sha256(path),
        "rows": len(frame),
        "columns": frame.columns.tolist(),
        "column_count": len(frame.columns),
        "season_min": int(season.min()),
        "season_max": int(season.max()),
        "unique_players_by_id": int(frame["Id"].nunique()),
        "unique_player_names": int(frame["Player"].nunique()),
        "unique_teams": int(frame["Team"].nunique()),
        "exact_duplicate_rows": int(frame.duplicated().sum()),
        "duplicate_key_rows": int(frame.duplicated(KEY_COLUMNS, keep=False).sum()),
        "blank_counts": {
            key: int(value) for key, value in blank_counts.items() if value > 0
        },
        "dash_placeholder_counts": {
            key: int(value) for key, value in placeholder_counts.items() if value > 0
        },
        "age_range": [int(age.min()), int(age.max())],
        "age_birth_year_mismatch_rows": int(age_mismatch.sum()),
        "invalid_birth_date_rows": int(born_year.isna().sum()),
        "suspicious_age_rows": suspicious_age.to_dict(orient="records"),
        "identity_conflicts": identity_conflicts(frame),
        "same_name_multiple_id_count": len(duplicated_names),
        "same_name_multiple_id_samples": {
            str(key): int(value) for key, value in duplicated_names.head(20).items()
        },
        "team_values": sorted(frame["Team"].unique().tolist()),
        "rows_by_season": {
            str(key): int(value)
            for key, value in frame.groupby("Season", sort=True).size().items()
        },
    }


def sequence_profile(frame: pd.DataFrame) -> dict[str, int]:
    """연속 과거 시즌과 다음 시즌 target을 가진 ML 후보 행 수를 센다."""

    player_seasons = {
        str(player_id): set(group["Season"].astype(int).tolist())
        for player_id, group in frame[["Id", "Season"]].drop_duplicates().groupby("Id")
    }
    result: dict[str, int] = {}
    for history_length in (1, 3, 5):
        eligible = 0
        for seasons in player_seasons.values():
            for season in seasons:
                required = range(season - history_length + 1, season + 2)
                if all(required_season in seasons for required_season in required):
                    eligible += 1
        result[f"consecutive_{history_length}_year_history_with_next_season"] = eligible
    return result


def batting_profile(frame: pd.DataFrame, path: Path) -> dict[str, Any]:
    """타격 데이터의 도메인 규칙과 계산된 비율을 검증한다."""

    profile = common_profile(frame, path)
    count_columns = [
        "Age", "Season", "G", "PA", "AB", "R", "H", "2B", "3B", "HR",
        "TB", "RBI", "SB", "CS", "BB", "HBP", "SO", "GDP", "SF", "SH", "E",
    ]
    rate_columns = ["AVG", "SLG", "OBP", "OPS"]
    profile["numeric_summary"] = numeric_summary(frame, count_columns + rate_columns)
    profile["ml_sequence_candidates"] = sequence_profile(frame)

    ab = to_number(frame["AB"])
    hits = to_number(frame["H"])
    total_bases = to_number(frame["TB"])
    walks = to_number(frame["BB"])
    hit_by_pitch = to_number(frame["HBP"])
    sacrifice_flies = to_number(frame["SF"])
    avg = to_number(frame["AVG"])
    slg = to_number(frame["SLG"])
    obp = to_number(frame["OBP"])
    ops = to_number(frame["OPS"])

    calculated_avg = hits / ab.replace(0, np.nan)
    calculated_slg = total_bases / ab.replace(0, np.nan)
    obp_denominator = ab + walks + hit_by_pitch + sacrifice_flies
    calculated_obp = (hits + walks + hit_by_pitch) / obp_denominator.replace(0, np.nan)

    profile["domain_checks"] = {
        "hits_greater_than_at_bats": int((hits > ab).sum()),
        "pa_less_than_ab": int((to_number(frame["PA"]) < ab).sum()),
        "avg_formula_mismatch_over_0_0015": int(
            ((avg - calculated_avg).abs() > 0.0015).sum()
        ),
        "slg_formula_mismatch_over_0_0015": int(
            ((slg - calculated_slg).abs() > 0.0015).sum()
        ),
        "obp_formula_mismatch_over_0_0015": int(
            ((obp - calculated_obp).abs() > 0.0015).sum()
        ),
        "ops_sum_mismatch_over_0_0015": int(((ops - obp - slg).abs() > 0.0015).sum()),
    }
    return profile


def pitching_profile(frame: pd.DataFrame, path: Path) -> dict[str, Any]:
    """투구 데이터의 야구식 이닝과 비율 지표를 검증한다."""

    profile = common_profile(frame, path)
    count_columns = [
        "Age", "Season", "ERA", "G", "CG", "SHO", "W", "L", "SV", "HLD",
        "WPCT", "TBF", "H", "HR", "BB", "HBP", "SO", "R", "ER",
    ]
    profile["numeric_summary"] = numeric_summary(frame, count_columns)
    profile["ml_sequence_candidates"] = sequence_profile(frame)

    innings_outs, invalid_innings = innings_to_outs(frame["IP"])
    earned_runs = to_number(frame["ER"])
    era = to_number(frame["ERA"])
    calculated_era = earned_runs * 27 / innings_outs.replace(0, np.nan)
    wins = to_number(frame["W"])
    losses = to_number(frame["L"])
    calculated_wpct = wins / (wins + losses).replace(0, np.nan)
    wpct = to_number(frame["WPCT"])

    profile["innings"] = {
        "missing_or_placeholder": int(frame["IP"].str.strip().isin(["", "-"]).sum()),
        "invalid_values": invalid_innings,
        "total_outs": int(innings_outs.sum()),
        "zero_out_rows": int((innings_outs == 0).sum()),
    }
    profile["domain_checks"] = {
        "earned_runs_greater_than_runs": int((earned_runs > to_number(frame["R"])).sum()),
        "era_formula_mismatch_over_0_015": int(
            ((era - calculated_era).abs() > 0.015).sum()
        ),
        "wpct_formula_mismatch_over_0_0015": int(
            ((wpct - calculated_wpct).abs() > 0.0015).sum()
        ),
    }
    return profile


def cross_file_profile(batting: pd.DataFrame, pitching: pd.DataFrame) -> dict[str, Any]:
    """두 역할을 함께 수행한 선수와 파일 간 신원 불일치를 확인한다."""

    batting_players = batting[["Id", "Player", "Born"]].drop_duplicates("Id")
    pitching_players = pitching[["Id", "Player", "Born"]].drop_duplicates("Id")
    joined = batting_players.merge(
        pitching_players,
        on="Id",
        how="inner",
        suffixes=("_batting", "_pitching"),
    )
    conflict = joined[
        (joined["Player_batting"] != joined["Player_pitching"])
        | (joined["Born_batting"] != joined["Born_pitching"])
    ]
    return {
        "players_in_both_files": len(joined),
        "identity_conflict_count": len(conflict),
        "identity_conflict_samples": conflict.head(20).to_dict(orient="records"),
    }


def main() -> None:
    """두 원본을 분석하고 하나의 기계 판독 가능 보고서로 저장한다."""

    args = parse_args()
    batting = load_raw_csv(args.batting)
    pitching = load_raw_csv(args.pitching)

    result = {
        "batting": batting_profile(batting, args.batting),
        "pitching": pitching_profile(pitching, args.pitching),
        "cross_file": cross_file_profile(batting, pitching),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"데이터 프로파일 저장 완료: {args.output}")


if __name__ == "__main__":
    main()
