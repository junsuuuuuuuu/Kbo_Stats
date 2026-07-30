"""Idempotent persistence for normalized KBO game box scores."""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.boxscore import GameBattingLine, GameBoxscoreSnapshot, GamePitchingLine
from app.services.kbo_team_schedule import TeamGameDetail
from app.services.recent_boxscore import innings_to_outs


def save_game_detail(session: Session, detail: TeamGameDetail, season: int) -> None:
    game_date = date.fromisoformat(detail.game_date)
    teams = (detail.away, detail.home)
    batting_complete = all(
        hitter.at_bats == 0 or hitter.total_bases is not None
        for team in teams
        for hitter in team.hitters
    )
    pitching_complete = all(
        innings_to_outs(pitcher.innings_pitched) is not None
        for team in teams
        for pitcher in team.pitchers
    )
    status = "collected" if batting_complete and pitching_complete else "partial"
    snapshot = session.scalar(
        select(GameBoxscoreSnapshot).where(GameBoxscoreSnapshot.game_id == detail.game_id)
    )
    values = {
        "season": season,
        "game_date": game_date,
        "source_url": detail.source_url,
        "status": status,
        "error_message": None,
    }
    if snapshot is None:
        session.add(GameBoxscoreSnapshot(game_id=detail.game_id, **values))
    else:
        for key, value in values.items():
            setattr(snapshot, key, value)
    session.flush()
    session.execute(delete(GameBattingLine).where(GameBattingLine.game_id == detail.game_id))
    session.execute(delete(GamePitchingLine).where(GamePitchingLine.game_id == detail.game_id))
    for team in teams:
        for line_order, hitter in enumerate(team.hitters, start=1):
            session.add(
                GameBattingLine(
                    game_id=detail.game_id,
                    game_date=game_date,
                    team_code=team.team_code,
                    player_name=hitter.player_name,
                    line_order=line_order,
                    plate_appearances=len(hitter.plate_appearances),
                    at_bats=hitter.at_bats,
                    hits=hitter.hits,
                    doubles=hitter.doubles,
                    triples=hitter.triples,
                    home_runs=hitter.home_runs,
                    runs=hitter.runs,
                    runs_batted_in=hitter.runs_batted_in,
                    walks=hitter.walks,
                    hit_by_pitch=hitter.hit_by_pitch,
                    sacrifice_flies=hitter.sacrifice_flies,
                    strikeouts=None,
                    total_bases=hitter.total_bases,
                    source_complete=hitter.at_bats == 0 or hitter.total_bases is not None,
                )
            )
        for line_order, pitcher in enumerate(team.pitchers, start=1):
            session.add(
                GamePitchingLine(
                    game_id=detail.game_id,
                    game_date=game_date,
                    team_code=team.team_code,
                    player_name=pitcher.player_name,
                    line_order=line_order,
                    appearance=pitcher.appearance,
                    is_starter="선발" in pitcher.appearance,
                    innings_pitched_outs=innings_to_outs(pitcher.innings_pitched),
                    hits_allowed=pitcher.hits_allowed,
                    home_runs_allowed=pitcher.home_runs_allowed,
                    walks_allowed=pitcher.walks_and_hit_batters,
                    hit_batters=0,
                    strikeouts=pitcher.strikeouts,
                    runs_allowed=pitcher.runs_allowed,
                    earned_runs=pitcher.earned_runs,
                    source_complete=innings_to_outs(pitcher.innings_pitched) is not None,
                )
            )
