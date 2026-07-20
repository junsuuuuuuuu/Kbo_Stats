"""선수 성장곡선 분석에 사용하는 역할별 지표 계약."""

from dataclasses import dataclass
from pathlib import Path

from app.ml.config import PROJECT_ROOT


@dataclass(frozen=True, slots=True)
class GrowthMetricSpec:
    """지표 표시명과 경기력 개선 방향."""

    column: str
    label: str
    higher_is_better: bool = True


@dataclass(frozen=True, slots=True)
class GrowthRoleSpec:
    """역할별 데이터와 유효 시즌 표본 기준."""

    role: str
    source_path: Path
    opportunity_column: str
    minimum_opportunity: int
    metrics: tuple[GrowthMetricSpec, ...]


BATTING_GROWTH_SPEC = GrowthRoleSpec(
    role="batting",
    source_path=PROJECT_ROOT / "data" / "processed" / "batting_stats_clean.csv",
    opportunity_column="plate_appearances",
    minimum_opportunity=100,
    metrics=(
        GrowthMetricSpec("batting_average", "타율"),
        GrowthMetricSpec("on_base_percentage", "출루율"),
        GrowthMetricSpec("slugging_percentage", "장타율"),
        GrowthMetricSpec("on_base_plus_slugging", "OPS"),
        GrowthMetricSpec("home_runs", "홈런"),
        GrowthMetricSpec("runs_batted_in", "타점"),
        GrowthMetricSpec("stolen_bases", "도루"),
        GrowthMetricSpec("walks", "볼넷"),
        GrowthMetricSpec("strikeouts", "삼진", higher_is_better=False),
    ),
)

PITCHING_GROWTH_SPEC = GrowthRoleSpec(
    role="pitching",
    source_path=PROJECT_ROOT / "data" / "processed" / "pitching_stats_clean.csv",
    opportunity_column="innings_pitched_outs",
    minimum_opportunity=90,
    metrics=(
        GrowthMetricSpec("earned_run_average", "ERA", higher_is_better=False),
        GrowthMetricSpec("innings_pitched_outs", "이닝(아웃카운트)"),
        GrowthMetricSpec("strikeouts", "탈삼진"),
        GrowthMetricSpec("walks_allowed", "허용 볼넷", higher_is_better=False),
        GrowthMetricSpec("saves", "세이브"),
        GrowthMetricSpec("holds", "홀드"),
    ),
)

GROWTH_SPECS: dict[str, GrowthRoleSpec] = {
    "batting": BATTING_GROWTH_SPEC,
    "pitching": PITCHING_GROWTH_SPEC,
}

BREAKOUT_PERCENTILE = 0.90
DECLINE_PERCENTILE = 0.10
