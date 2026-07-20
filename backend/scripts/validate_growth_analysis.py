"""실제 정제 데이터로 성장곡선과 이벤트 탐지를 재현한다."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.ml.artifacts import file_sha256, write_json
from app.ml.growth import PlayerGrowthAnalyzer
from app.ml.growth_config import GROWTH_SPECS, GrowthRoleSpec

REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "ml"
    / "reports"
    / ("growth_analysis_validation.json")
)


def _select_long_career(frame: pd.DataFrame, spec: GrowthRoleSpec) -> int:
    qualified = frame.loc[frame[spec.opportunity_column] >= spec.minimum_opportunity]
    return int(qualified.groupby("player_id").size().idxmax())


def _role_report(
    role: str,
    frame: pd.DataFrame,
    analyzer: PlayerGrowthAnalyzer,
) -> dict[str, object]:
    spec = GROWTH_SPECS[role]
    player_id = _select_long_career(frame, spec)
    result = analyzer.analyze(role, player_id)
    event_counts = result.events.groupby(["metric", "event"]).size().rename("count").reset_index()
    return {
        "reference_player_id": player_id,
        "career_season_count": result.player["season_count"],
        "curve_point_count": len(result.curves),
        "event_count": len(result.events),
        "events_by_metric": event_counts.to_dict(orient="records"),
        "league_thresholds": analyzer.league_change_thresholds(role).to_dict(orient="records"),
    }


def main() -> None:
    """역할별 최장 커리어 표본을 분석하고 데이터 checksum과 함께 저장한다."""

    frames = {
        role: pd.read_csv(spec.source_path, low_memory=False) for role, spec in GROWTH_SPECS.items()
    }
    analyzer = PlayerGrowthAnalyzer(frames)
    report = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "event_rule": "league consecutive-season performance change p10/p90",
        "sample_rule": {"batting_pa": 100, "pitching_outs": 90},
        "sources": {
            role: {
                "path": spec.source_path.name,
                "sha256": file_sha256(spec.source_path),
            }
            for role, spec in GROWTH_SPECS.items()
        },
        "roles": {role: _role_report(role, frame, analyzer) for role, frame in frames.items()},
    }
    write_json(REPORT_PATH, report)
    print(f"성장 분석 검증 보고서 저장 완료: {REPORT_PATH}")


if __name__ == "__main__":
    main()
