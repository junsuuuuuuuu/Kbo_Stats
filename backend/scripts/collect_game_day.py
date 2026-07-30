"""Collect a KBO game day and upsert the home-page snapshot."""

from __future__ import annotations

import argparse
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.game_day import GameDaySnapshot
from app.schemas.team import LatestGameDayResponse
from app.services.boxscore_store import save_game_detail
from app.services.kbo_team_schedule import kbo_team_schedule_client


def save_snapshot(session: Session, response: LatestGameDayResponse, season: int) -> None:
    snapshot = session.scalar(
        select(GameDaySnapshot).where(
            GameDaySnapshot.season == season,
            GameDaySnapshot.game_date == response.game_date,
        )
    )
    values = {
        "source_url": response.source_url,
        "payload": response.model_dump(mode="json"),
    }
    if snapshot is None:
        snapshot = GameDaySnapshot(season=season, game_date=response.game_date, **values)
        session.add(snapshot)
    else:
        snapshot.source_url = values["source_url"]
        snapshot.payload = values["payload"]
    for game in response.games:
        if game.status != "completed" or game.detail_status != "collected":
            continue
        try:
            detail = kbo_team_schedule_client.game_detail(game.game_id, season)
            save_game_detail(session, detail, season)
        except Exception as exception:  # noqa: BLE001 - one detail must not abort the day snapshot
            # The schedule snapshot remains usable when a single box score fails.
            print(f"박스스코어 저장 건너뜀: {game.game_id} ({exception})")
    session.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KBO 홈 경기 일정·결과 수집")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--date", type=date.fromisoformat)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    collected = (
        kbo_team_schedule_client.game_day(args.date.isoformat(), args.season)
        if args.date
        else kbo_team_schedule_client.latest_game_day(args.season)
    )
    response = LatestGameDayResponse.model_validate(collected, from_attributes=True)
    with SessionLocal() as session:
        save_snapshot(session, response, args.season)
    print(f"경기 스냅샷 저장 완료: {response.game_date} ({len(response.games)}경기)")


if __name__ == "__main__":
    main()
