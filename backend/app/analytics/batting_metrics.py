"""타자 시즌 원시 기록에서 파생 공격 지표를 계산한다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class BattingLine(Protocol):
    plate_appearances: int
    at_bats: int
    runs: int
    hits: int
    doubles: int
    triples: int
    home_runs: int
    stolen_bases: int
    caught_stealing: int
    walks: int
    hit_by_pitch: int
    strikeouts: int
    grounded_into_double_play: int
    sacrifice_flies: int
    batting_average: object
    slugging_percentage: object


@dataclass(frozen=True, slots=True)
class BattingMetricValues:
    walk_percentage: float | None
    strikeout_percentage: float | None
    walk_to_strikeout_ratio: float | None
    isolated_power: float | None
    batting_average_on_balls_in_play: float | None
    stolen_base_percentage: float | None
    speed_score: float | None
    weighted_stolen_base_runs: float | None
    weighted_double_play_runs: float | None
    weighted_on_base_average: float | None
    weighted_runs_above_average: float | None
    weighted_runs_created: float | None
    weighted_runs_created_plus: float | None


def _divide(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator > 0 else None


def _number(value: object) -> float | None:
    return None if value is None else float(value)


def _woba(line: BattingLine) -> float | None:
    singles = line.hits - line.doubles - line.triples - line.home_runs
    numerator = (
        0.69 * line.walks
        + 0.72 * line.hit_by_pitch
        + 0.89 * singles
        + 1.27 * line.doubles
        + 1.62 * line.triples
        + 2.10 * line.home_runs
    )
    denominator = line.at_bats + line.walks + line.hit_by_pitch + line.sacrifice_flies
    return _divide(numerator, denominator)


def _speed_score(line: BattingLine) -> float | None:
    """현재 확보된 기록으로 계산 가능한 Bill James 4요소 Spd(0~10)."""

    singles = line.hits - line.doubles - line.triples - line.home_runs
    components: list[float] = []
    attempts = line.stolen_bases + line.caught_stealing
    components.append(((line.stolen_bases + 3) / (attempts + 7) - 0.4) * 20)

    reach_base = singles + line.walks + line.hit_by_pitch
    if reach_base > 0:
        components.append(((attempts / reach_base) ** 0.5) * 14.3)

    balls_available = line.at_bats - line.home_runs - line.strikeouts
    if balls_available > 0:
        components.append(line.triples / balls_available * 400)

    run_opportunities = line.hits + line.walks + line.hit_by_pitch - line.home_runs
    if run_opportunities > 0:
        components.append((line.runs - line.home_runs) / run_opportunities * 25)

    if not components:
        return None
    return sum(max(0.0, min(10.0, value)) for value in components) / len(components)


def calculate_batting_metrics(
    line: BattingLine,
    league_lines: list[BattingLine],
) -> BattingMetricValues:
    """시즌 리그 합계를 기준으로 타자 파생 지표를 계산한다.

    KBO 원자료에 IBB, GDP 기회, 구장 계수가 없으므로 wOBA는 비고의도 BB를
    구분하지 않고, wGDP는 인플레이 타구를 기회로 삼은 추정값이며 wRC+는
    구장 비보정 값이다.
    """

    walk_rate = _divide(line.walks, line.plate_appearances)
    strikeout_rate = _divide(line.strikeouts, line.plate_appearances)
    bb_k = _divide(line.walks, line.strikeouts)
    avg = _number(line.batting_average)
    slg = _number(line.slugging_percentage)
    iso = slg - avg if slg is not None and avg is not None else None
    babip = _divide(
        line.hits - line.home_runs,
        line.at_bats - line.strikeouts - line.home_runs + line.sacrifice_flies,
    )
    sb_percentage = _divide(
        line.stolen_bases, line.stolen_bases + line.caught_stealing
    )

    league_pa = sum(item.plate_appearances for item in league_lines)
    league_runs = sum(item.runs for item in league_lines)
    league_woba_numerator = sum(
        (_woba(item) or 0)
        * (item.at_bats + item.walks + item.hit_by_pitch + item.sacrifice_flies)
        for item in league_lines
    )
    league_woba_denominator = sum(
        item.at_bats + item.walks + item.hit_by_pitch + item.sacrifice_flies
        for item in league_lines
    )
    league_woba = _divide(league_woba_numerator, league_woba_denominator)
    woba = _woba(line)
    woba_scale = 1.15
    league_runs_per_pa = _divide(league_runs, league_pa)
    wraa = (
        (woba - league_woba) / woba_scale * line.plate_appearances
        if woba is not None and league_woba is not None
        else None
    )
    wrc = (
        wraa + league_runs_per_pa * line.plate_appearances
        if wraa is not None and league_runs_per_pa is not None
        else None
    )
    wrc_plus = (
        ((wraa / line.plate_appearances + league_runs_per_pa) / league_runs_per_pa * 100)
        if wraa is not None
        and line.plate_appearances > 0
        and league_runs_per_pa is not None
        and league_runs_per_pa > 0
        else None
    )

    singles = line.hits - line.doubles - line.triples - line.home_runs
    sb_opportunities = singles + line.walks + line.hit_by_pitch
    league_sb = sum(item.stolen_bases for item in league_lines)
    league_cs = sum(item.caught_stealing for item in league_lines)
    league_sb_opportunities = sum(
        item.hits - item.doubles - item.triples - item.home_runs + item.walks + item.hit_by_pitch
        for item in league_lines
    )
    league_sb_runs_per_opportunity = _divide(
        league_sb * 0.20 - league_cs * 0.40, league_sb_opportunities
    )
    wsb = (
        line.stolen_bases * 0.20
        - line.caught_stealing * 0.40
        - league_sb_runs_per_opportunity * sb_opportunities
        if league_sb_runs_per_opportunity is not None
        else None
    )

    bip = line.at_bats - line.strikeouts - line.home_runs
    league_bip = sum(item.at_bats - item.strikeouts - item.home_runs for item in league_lines)
    league_gdp = sum(item.grounded_into_double_play for item in league_lines)
    league_gdp_rate = _divide(league_gdp, league_bip)
    wgdp = (
        (league_gdp_rate * bip - line.grounded_into_double_play) * 0.37
        if league_gdp_rate is not None and bip > 0
        else None
    )

    return BattingMetricValues(
        walk_percentage=walk_rate,
        strikeout_percentage=strikeout_rate,
        walk_to_strikeout_ratio=bb_k,
        isolated_power=iso,
        batting_average_on_balls_in_play=babip,
        stolen_base_percentage=sb_percentage,
        speed_score=_speed_score(line),
        weighted_stolen_base_runs=wsb,
        weighted_double_play_runs=wgdp,
        weighted_on_base_average=woba,
        weighted_runs_above_average=wraa,
        weighted_runs_created=wrc,
        weighted_runs_created_plus=wrc_plus,
    )
