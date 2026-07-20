"""선수 조건 검색과 유사도 계산에 사용하는 역할별 명세."""

from dataclasses import dataclass
from pathlib import Path

from app.ml.config import PROJECT_ROOT


@dataclass(frozen=True, slots=True)
class RecommendationSpec:
    """추천 후보의 품질 기준과 비교 feature 계약."""

    role: str
    source_path: Path
    opportunity_column: str
    minimum_opportunity: int
    similarity_features: tuple[str, ...]
    reason_features: tuple[str, ...]
    filterable_columns: tuple[str, ...]
    default_sort_column: str
    default_sort_ascending: bool


BATTING_RECOMMENDATION_SPEC = RecommendationSpec(
    role="batting",
    source_path=PROJECT_ROOT / "data" / "processed" / "batting_stats_clean.csv",
    opportunity_column="plate_appearances",
    minimum_opportunity=100,
    similarity_features=(
        "age",
        "games",
        "plate_appearances",
        "batting_average",
        "on_base_percentage",
        "slugging_percentage",
        "on_base_plus_slugging",
        "home_runs",
        "runs_batted_in",
        "stolen_bases",
        "walks",
        "strikeouts",
    ),
    reason_features=(
        "batting_average",
        "on_base_percentage",
        "slugging_percentage",
        "on_base_plus_slugging",
        "home_runs",
        "runs_batted_in",
        "stolen_bases",
        "walks",
        "strikeouts",
    ),
    filterable_columns=(
        "age",
        "games",
        "plate_appearances",
        "batting_average",
        "on_base_percentage",
        "slugging_percentage",
        "on_base_plus_slugging",
        "home_runs",
        "runs_batted_in",
        "stolen_bases",
        "walks",
        "strikeouts",
    ),
    default_sort_column="on_base_plus_slugging",
    default_sort_ascending=False,
)

PITCHING_RECOMMENDATION_SPEC = RecommendationSpec(
    role="pitching",
    source_path=PROJECT_ROOT / "data" / "processed" / "pitching_stats_clean.csv",
    opportunity_column="innings_pitched_outs",
    minimum_opportunity=90,
    similarity_features=(
        "age",
        "games",
        "innings_pitched_outs",
        "earned_run_average",
        "wins",
        "losses",
        "saves",
        "holds",
        "hits_allowed",
        "home_runs_allowed",
        "walks_allowed",
        "strikeouts",
    ),
    reason_features=(
        "earned_run_average",
        "wins",
        "saves",
        "holds",
        "hits_allowed",
        "home_runs_allowed",
        "walks_allowed",
        "strikeouts",
    ),
    filterable_columns=(
        "age",
        "games",
        "innings_pitched_outs",
        "earned_run_average",
        "wins",
        "losses",
        "saves",
        "holds",
        "hits_allowed",
        "home_runs_allowed",
        "walks_allowed",
        "strikeouts",
    ),
    default_sort_column="earned_run_average",
    default_sort_ascending=True,
)

RECOMMENDATION_SPECS: dict[str, RecommendationSpec] = {
    "batting": BATTING_RECOMMENDATION_SPEC,
    "pitching": PITCHING_RECOMMENDATION_SPEC,
}

METRIC_LABELS = {
    "batting_average": "타율",
    "on_base_percentage": "출루율",
    "slugging_percentage": "장타율",
    "on_base_plus_slugging": "OPS",
    "home_runs": "홈런",
    "runs_batted_in": "타점",
    "stolen_bases": "도루",
    "walks": "볼넷",
    "strikeouts": "탈삼진",
    "earned_run_average": "ERA",
    "wins": "승",
    "saves": "세이브",
    "holds": "홀드",
    "hits_allowed": "피안타",
    "home_runs_allowed": "피홈런",
    "walks_allowed": "허용 볼넷",
}
