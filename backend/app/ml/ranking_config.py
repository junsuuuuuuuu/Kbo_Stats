"""설명 가능한 AI 선수 가치 점수의 역할별 가중치 계약."""

from dataclasses import dataclass
from pathlib import Path

from app.ml.config import PROJECT_ROOT


@dataclass(frozen=True, slots=True)
class RankingSpec:
    role: str
    source_path: Path
    opportunity_column: str
    minimum_opportunity: int
    primary_metric: str
    component_weights: dict[str, float]


RANKING_SPECS: dict[str, RankingSpec] = {
    "batting": RankingSpec(
        role="batting",
        source_path=PROJECT_ROOT / "data" / "processed" / "batting_stats_clean.csv",
        opportunity_column="plate_appearances",
        minimum_opportunity=100,
        primary_metric="on_base_plus_slugging",
        component_weights={
            "offense_score": 0.20,
            "on_base_score": 0.12,
            "power_score": 0.16,
            "speed_score": 0.07,
            "defense_score": 0.15,
            "consistency_score": 0.10,
            "availability_score": 0.08,
            "age_potential_score": 0.05,
            "team_contribution_score": 0.07,
        },
    ),
    "pitching": RankingSpec(
        role="pitching",
        source_path=PROJECT_ROOT / "data" / "processed" / "pitching_stats_clean.csv",
        opportunity_column="innings_pitched_outs",
        minimum_opportunity=90,
        primary_metric="earned_run_average",
        component_weights={
            "run_prevention_score": 0.25,
            "strikeout_score": 0.18,
            "control_score": 0.12,
            "leverage_score": 0.10,
            "consistency_score": 0.10,
            "workload_score": 0.13,
            "age_potential_score": 0.05,
            "team_contribution_score": 0.07,
        },
    ),
}

COMPONENT_LABELS = {
    "offense_score": "종합 공격력",
    "on_base_score": "출루 능력",
    "power_score": "장타력",
    "speed_score": "주루 기여",
    "defense_score": "수비 기여",
    "run_prevention_score": "실점 억제",
    "strikeout_score": "탈삼진 능력",
    "control_score": "제구력",
    "leverage_score": "승리조 기여",
    "consistency_score": "꾸준함",
    "availability_score": "출장 기여",
    "workload_score": "이닝·출장 기여",
    "age_potential_score": "나이 잠재력",
    "team_contribution_score": "팀 내 기여 비중",
}
