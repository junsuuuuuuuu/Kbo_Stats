"""다음 시즌 예측 target과 역할별 feature 명세."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_ROOT = Path(__file__).resolve().parent / "artifacts" / "next_season"
REPORT_ROOT = Path(__file__).resolve().parent / "reports"
RANDOM_STATE = 42
N_JOBS = int(os.getenv("ML_N_JOBS", "1"))
MODEL_VERSION = "1.0.0"
HISTORY_YEARS = 3
VALIDATION_YEARS = (2021, 2022, 2023, 2024, 2025)
TUNING_YEAR = 2020


@dataclass(frozen=True, slots=True)
class TargetSpec:
    """한 예측 target의 입력, 최소 표본과 출력 범위 계약."""

    role: str
    target: str
    source_path: Path
    numeric_metrics: tuple[str, ...]
    categorical_features: tuple[str, ...]
    opportunity_column: str
    minimum_target_opportunity: int
    prediction_min: float
    prediction_max: float | None

    @property
    def key(self) -> str:
        """artifact 디렉터리와 모델 registry에서 사용할 안정적인 key."""

        return f"{self.role}_{self.target}"


BATTING_METRICS = (
    "age",
    "games",
    "plate_appearances",
    "at_bats",
    "runs",
    "hits",
    "home_runs",
    "runs_batted_in",
    "stolen_bases",
    "walks",
    "strikeouts",
    "batting_average",
    "on_base_percentage",
    "slugging_percentage",
    "on_base_plus_slugging",
)
PITCHING_METRICS = (
    "age",
    "games",
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
    "earned_runs",
    "earned_run_average",
)


TARGET_SPECS: dict[str, TargetSpec] = {
    "batting_average": TargetSpec(
        role="batting",
        target="batting_average",
        source_path=PROJECT_ROOT / "data" / "processed" / "batting_stats_clean.csv",
        numeric_metrics=BATTING_METRICS,
        categorical_features=("team", "position"),
        opportunity_column="plate_appearances",
        minimum_target_opportunity=100,
        prediction_min=0.0,
        prediction_max=1.0,
    ),
    "on_base_plus_slugging": TargetSpec(
        role="batting",
        target="on_base_plus_slugging",
        source_path=PROJECT_ROOT / "data" / "processed" / "batting_stats_clean.csv",
        numeric_metrics=BATTING_METRICS,
        categorical_features=("team", "position"),
        opportunity_column="plate_appearances",
        minimum_target_opportunity=100,
        prediction_min=0.0,
        prediction_max=5.0,
    ),
    "home_runs": TargetSpec(
        role="batting",
        target="home_runs",
        source_path=PROJECT_ROOT / "data" / "processed" / "batting_stats_clean.csv",
        numeric_metrics=BATTING_METRICS,
        categorical_features=("team", "position"),
        opportunity_column="plate_appearances",
        minimum_target_opportunity=20,
        prediction_min=0.0,
        prediction_max=None,
    ),
    "earned_run_average": TargetSpec(
        role="pitching",
        target="earned_run_average",
        source_path=PROJECT_ROOT / "data" / "processed" / "pitching_stats_clean.csv",
        numeric_metrics=PITCHING_METRICS,
        categorical_features=("team",),
        opportunity_column="innings_pitched_outs",
        minimum_target_opportunity=150,
        prediction_min=0.0,
        prediction_max=None,
    ),
    "strikeouts": TargetSpec(
        role="pitching",
        target="strikeouts",
        source_path=PROJECT_ROOT / "data" / "processed" / "pitching_stats_clean.csv",
        numeric_metrics=PITCHING_METRICS,
        categorical_features=("team",),
        opportunity_column="innings_pitched_outs",
        minimum_target_opportunity=3,
        prediction_min=0.0,
        prediction_max=None,
    ),
}
