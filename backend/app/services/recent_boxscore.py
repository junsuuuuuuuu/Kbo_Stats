"""Official baseball-stat calculations over a bounded set of game box scores."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.kbo_team_schedule import TeamGameDetail


@dataclass(frozen=True)
class RecentBoxscoreMetrics:
    batting_average: float | None = None
    ops: float | None = None
    era: float | None = None
    whip: float | None = None
    strikeouts_per_game: float | None = None
    batting_status: str = "unavailable"
    pitching_status: str = "unavailable"


def innings_to_outs(value: str) -> int | None:
    """Convert baseball innings notation (6, 6.1, 6.2) to outs."""

    match = re.fullmatch(r"\s*(\d+)(?:\.(\d))?\s*", value)
    if match is None:
        return None
    completed = int(match.group(1))
    remainder = int(match.group(2) or 0)
    if remainder not in {0, 1, 2}:
        return None
    return completed * 3 + remainder


def aggregate_boxscores(details: list[TeamGameDetail], team_code: str) -> RecentBoxscoreMetrics:
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
    batting_status = (
        "complete" if hitters and all(value is not None for value in total_bases) else "partial"
    )
    ops = None
    if batting_average is not None and batting_status == "complete":
        on_base_denominator = at_bats + walks + hit_by_pitch + sacrifice_flies
        slugging = sum(value or 0 for value in total_bases) / at_bats if at_bats else None
        on_base = (
            (hits + walks + hit_by_pitch) / on_base_denominator if on_base_denominator else None
        )
        ops = on_base + slugging if on_base is not None and slugging is not None else None
    outs = [innings_to_outs(pitcher.innings_pitched) for pitcher in pitchers]
    pitching_status = (
        "complete" if pitchers and all(value is not None for value in outs) else "partial"
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
        batting_average=batting_average,
        ops=ops,
        era=era,
        whip=whip,
        strikeouts_per_game=strikeouts_per_game,
        batting_status=batting_status if hitters else "unavailable",
        pitching_status=pitching_status if pitchers else "unavailable",
    )
