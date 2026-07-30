"""Official baseball-stat calculations over a bounded set of game box scores."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.kbo_team_schedule import TeamGameDetail


@dataclass(frozen=True)
class RecentBoxscoreMetrics:
    boxscore_games: int = 0
    expected_games: int = 0
    batting_average: float | None = None
    on_base_percentage: float | None = None
    slugging_percentage: float | None = None
    ops: float | None = None
    hits_per_game: float | None = None
    home_runs: int | None = None
    walks: int | None = None
    era: float | None = None
    whip: float | None = None
    strikeouts_per_game: float | None = None
    batting_average_status: str = "unavailable"
    on_base_percentage_status: str = "unavailable"
    slugging_percentage_status: str = "unavailable"
    ops_status: str = "unavailable"
    batting_status: str = "unavailable"
    pitching_status: str = "unavailable"


def innings_to_outs(value: str) -> int | None:
    """Convert baseball innings notation (6, 6.1, 6.2) to outs."""

    fraction = re.fullmatch(r"\s*(\d+)\s+(1|2)/3\s*", value)
    if fraction is not None:
        return int(fraction.group(1)) * 3 + int(fraction.group(2))
    fraction = re.fullmatch(r"\s*(\d+)/(1|2|3)\s*", value)
    if fraction is not None:
        numerator = int(fraction.group(1))
        denominator = int(fraction.group(2))
        if denominator == 3 and numerator in {1, 2}:
            return numerator
        return None
    match = re.fullmatch(r"\s*(\d+)(?:\.(\d))?\s*", value)
    if match is None:
        return None
    completed = int(match.group(1))
    remainder = int(match.group(2) or 0)
    if remainder not in {0, 1, 2}:
        return None
    return completed * 3 + remainder


def aggregate_boxscores(
    details: list[TeamGameDetail], team_code: str, expected_games: int | None = None
) -> RecentBoxscoreMetrics:
    expected = expected_games if expected_games is not None else len(details)
    teams = [
        team
        for detail in details
        for team in (detail.away, detail.home)
        if team.team_code == team_code
    ]
    hitters = [hitter for team in teams for hitter in team.hitters]
    pitchers = [pitcher for team in teams for pitcher in team.pitchers]

    at_bats = sum(hitter.at_bats for hitter in hitters)
    hits = sum(hitter.hits for hitter in hitters)
    total_bases = [hitter.total_bases for hitter in hitters]
    walks = sum(team.walks for team in teams)
    hit_by_pitch = sum(hitter.hit_by_pitch for hitter in hitters)
    sacrifice_flies = sum(hitter.sacrifice_flies for hitter in hitters)
    batting_average = hits / at_bats if at_bats else None
    has_batting_components = bool(hitters) and all(value is not None for value in total_bases)
    coverage_status = "available" if details and len(details) >= expected else "partial"
    if not details:
        coverage_status = "unavailable"
    batting_status = (
        coverage_status if has_batting_components else ("partial" if details else "unavailable")
    )
    on_base_percentage = None
    slugging_percentage = None
    ops = None
    if batting_average is not None:
        on_base_denominator = at_bats + walks + hit_by_pitch + sacrifice_flies
        on_base_percentage = (
            (hits + walks + hit_by_pitch) / on_base_denominator if on_base_denominator else None
        )
        if has_batting_components:
            slugging_percentage = sum(value or 0 for value in total_bases) / at_bats
            ops = on_base_percentage + slugging_percentage
    outs = [innings_to_outs(pitcher.innings_pitched) for pitcher in pitchers]
    pitching_status = (
        "available" if pitchers and all(value is not None for value in outs) else "partial"
    )
    total_outs = sum(value or 0 for value in outs)
    earned_runs = sum(pitcher.earned_runs for pitcher in pitchers)
    hits_allowed = sum(pitcher.hits_allowed for pitcher in pitchers)
    walks_allowed = sum(pitcher.walks_and_hit_batters for pitcher in pitchers)
    era = earned_runs * 27 / total_outs if total_outs else None
    whip = (hits_allowed + walks_allowed) * 3 / total_outs if total_outs else None
    strikeouts_per_game = (
        sum(pitcher.strikeouts for pitcher in pitchers) / len(details) if details else None
    )
    return RecentBoxscoreMetrics(
        boxscore_games=len(details),
        expected_games=expected,
        batting_average=batting_average,
        on_base_percentage=on_base_percentage,
        slugging_percentage=slugging_percentage,
        ops=ops,
        hits_per_game=hits / len(details) if details else None,
        home_runs=sum(hitter.home_runs for hitter in hitters) if hitters else None,
        walks=walks if hitters else None,
        era=era,
        whip=whip,
        strikeouts_per_game=strikeouts_per_game,
        batting_average_status=(coverage_status if batting_average is not None else "unavailable"),
        on_base_percentage_status=(
            coverage_status if on_base_percentage is not None else "unavailable"
        ),
        slugging_percentage_status=(
            coverage_status if slugging_percentage is not None else "unavailable"
        ),
        ops_status=(coverage_status if ops is not None else "unavailable"),
        batting_status=batting_status if hitters else "unavailable",
        pitching_status=pitching_status if pitchers else "unavailable",
    )


def aggregate_boxscore_rows(
    batting_lines: list[object],
    pitching_lines: list[object],
    expected_games: int,
) -> RecentBoxscoreMetrics:
    """Aggregate normalized DB lines using the official baseball formulas."""

    batting_game_ids = {line.game_id for line in batting_lines}
    pitching_game_ids = {line.game_id for line in pitching_lines}
    boxscore_games = len(batting_game_ids)
    batting_complete = bool(batting_lines) and all(
        getattr(line, "source_complete", False) for line in batting_lines
    )
    pitching_complete = bool(pitching_lines) and all(
        getattr(line, "source_complete", False) for line in pitching_lines
    )
    at_bats = sum(getattr(line, "at_bats", 0) or 0 for line in batting_lines)
    hits = sum(getattr(line, "hits", 0) or 0 for line in batting_lines)
    walks = sum(getattr(line, "walks", 0) or 0 for line in batting_lines)
    hit_by_pitch = sum(getattr(line, "hit_by_pitch", 0) or 0 for line in batting_lines)
    sacrifice_flies = sum(getattr(line, "sacrifice_flies", 0) or 0 for line in batting_lines)
    total_bases = sum(getattr(line, "total_bases", 0) or 0 for line in batting_lines)
    on_base_denominator = at_bats + walks + hit_by_pitch + sacrifice_flies
    batting_average = hits / at_bats if at_bats else None
    on_base_percentage = (
        (hits + walks + hit_by_pitch) / on_base_denominator
        if on_base_denominator
        else None
    )
    slugging_percentage = total_bases / at_bats if at_bats and batting_complete else None
    ops = (
        on_base_percentage + slugging_percentage
        if on_base_percentage is not None and slugging_percentage is not None
        else None
    )
    outs = sum(getattr(line, "innings_pitched_outs", 0) or 0 for line in pitching_lines)
    earned_runs = sum(getattr(line, "earned_runs", 0) or 0 for line in pitching_lines)
    hits_allowed = sum(getattr(line, "hits_allowed", 0) or 0 for line in pitching_lines)
    walks_allowed = sum(getattr(line, "walks_allowed", 0) or 0 for line in pitching_lines)
    hit_batters = sum(getattr(line, "hit_batters", 0) or 0 for line in pitching_lines)
    strikeouts = sum(getattr(line, "strikeouts", 0) or 0 for line in pitching_lines)
    batting_status = (
        "available" if boxscore_games >= expected_games
        else "partial" if batting_lines else "unavailable"
    )
    pitching_status = (
        "available" if len(pitching_game_ids) >= expected_games
        else "partial" if pitching_lines else "unavailable"
    )
    metric_status = (
        "available" if batting_complete else "partial" if batting_lines else "unavailable"
    )
    return RecentBoxscoreMetrics(
        boxscore_games=boxscore_games,
        expected_games=expected_games,
        batting_average=batting_average,
        on_base_percentage=on_base_percentage,
        slugging_percentage=slugging_percentage,
        ops=ops,
        hits_per_game=hits / boxscore_games if boxscore_games else None,
        home_runs=sum(getattr(line, "home_runs", 0) or 0 for line in batting_lines),
        walks=walks,
        era=earned_runs * 9 / outs if outs and pitching_complete else None,
        whip=(hits_allowed + walks_allowed + hit_batters) / outs
        if outs and pitching_complete
        else None,
        strikeouts_per_game=strikeouts / boxscore_games if boxscore_games else None,
        batting_average_status=metric_status,
        on_base_percentage_status="available" if on_base_percentage is not None else "unavailable",
        slugging_percentage_status=metric_status,
        ops_status=metric_status if ops is not None else "unavailable",
        batting_status=batting_status,
        pitching_status=pitching_status,
    )
