"""선수 전성기 예측의 역할·target·시간 분할 계약."""

from dataclasses import dataclass
from pathlib import Path

from app.ml.config import BATTING_METRICS, PITCHING_METRICS, PROJECT_ROOT

PEAK_ARTIFACT_ROOT = Path(__file__).resolve().parent / "artifacts" / "peak"
PEAK_REPORT_PATH = Path(__file__).resolve().parent / "reports" / "peak_training_report.json"
PEAK_MODEL_VERSION = "1.0.0"
EARLY_CAREER_SEASONS = 3
MINIMUM_CAREER_SEASONS = 4
COMPLETED_CAREER_LAST_SEASON = 2022
TUNING_COHORT_START = 2005
VALIDATION_COHORT_START = 2010


@dataclass(frozen=True, slots=True)
class PeakRoleSpec:
    """초기 커리어 feature와 전성기 label 생성에 필요한 역할별 명세."""

    role: str
    source_path: Path
    opportunity_column: str
    minimum_opportunity: int
    numeric_metrics: tuple[str, ...]
    categorical_features: tuple[str, ...]
    primary_metric: str
    primary_higher_is_better: bool


@dataclass(frozen=True, slots=True)
class PeakTargetSpec:
    """개별 전성기 회귀 target의 출력 범위와 단순 기준선."""

    role: str
    target: str
    label: str
    prediction_min: float
    prediction_max: float
    baseline_feature: str
    baseline_relation: str

    @property
    def key(self) -> str:
        return f"{self.role}_{self.target}"


PEAK_ROLE_SPECS: dict[str, PeakRoleSpec] = {
    "batting": PeakRoleSpec(
        role="batting",
        source_path=PROJECT_ROOT / "data" / "processed" / "batting_stats_clean.csv",
        opportunity_column="plate_appearances",
        minimum_opportunity=100,
        numeric_metrics=BATTING_METRICS,
        categorical_features=("position",),
        primary_metric="on_base_plus_slugging",
        primary_higher_is_better=True,
    ),
    "pitching": PeakRoleSpec(
        role="pitching",
        source_path=PROJECT_ROOT / "data" / "processed" / "pitching_stats_clean.csv",
        opportunity_column="innings_pitched_outs",
        minimum_opportunity=90,
        numeric_metrics=PITCHING_METRICS,
        categorical_features=(),
        primary_metric="earned_run_average",
        primary_higher_is_better=False,
    ),
}

PEAK_TARGET_SPECS: dict[str, PeakTargetSpec] = {
    "batting_peak_age": PeakTargetSpec(
        "batting", "peak_age", "Peak Age", 18.0, 45.0, "feature_cutoff_age", "none"
    ),
    "batting_peak_ops": PeakTargetSpec(
        "batting", "peak_ops", "Peak OPS", 0.0, 2.0, "on_base_plus_slugging_max_3", "at_least"
    ),
    "batting_peak_home_runs": PeakTargetSpec(
        "batting", "peak_home_runs", "Peak HR", 0.0, 80.0, "home_runs_max_3", "at_least"
    ),
    "pitching_peak_age": PeakTargetSpec(
        "pitching", "peak_age", "Peak Age", 18.0, 45.0, "feature_cutoff_age", "none"
    ),
    "pitching_peak_era": PeakTargetSpec(
        "pitching", "peak_era", "Peak ERA", 0.0, 20.0, "earned_run_average_min_3", "at_most"
    ),
    "pitching_peak_strikeouts": PeakTargetSpec(
        "pitching", "peak_strikeouts", "Peak SO", 0.0, 350.0, "strikeouts_max_3", "at_least"
    ),
}
