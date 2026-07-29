"""Non-blocking, idempotent game-day synchronization for application startup."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, text

from app.database.session import SessionLocal
from app.models.game_day import GameDaySnapshot
from app.schemas.team import LatestGameDayResponse
from app.services.kbo_team_schedule import kbo_team_schedule_client
from scripts.collect_game_day import save_snapshot

logger = logging.getLogger("kbo_api")
SYNC_LOCK_NAME = "kbo_game_day_startup_sync"
SYNC_TTL = timedelta(minutes=30)


def _needs_refresh(snapshot: GameDaySnapshot | None, target: date, today: date) -> bool:
    if snapshot is None:
        return True
    if target < today:
        games = snapshot.payload.get("games", [])
        completed = any(game.get("status") == "completed" for game in games)
        return not completed or snapshot.updated_at < datetime.now() - SYNC_TTL
    return snapshot.updated_at < datetime.now() - SYNC_TTL


def run_startup_game_day_sync(season: int = 2026) -> None:
    """Refresh recent/future light snapshots without blocking API startup."""

    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    dates = [today - timedelta(days=1), today, today + timedelta(days=1), today + timedelta(days=2)]
    try:
        with SessionLocal() as session:
            acquired = session.scalar(text("SELECT GET_LOCK(:name, 0)"), {"name": SYNC_LOCK_NAME})
            if acquired != 1:
                logger.info("startup_game_day_sync_skipped reason=lock_held")
                return
            try:
                for target in dates:
                    snapshot = session.scalar(
                        select(GameDaySnapshot).where(
                            GameDaySnapshot.season == season,
                            GameDaySnapshot.game_date == target,
                        )
                    )
                    if not _needs_refresh(snapshot, target, today):
                        continue
                    try:
                        collected = kbo_team_schedule_client.game_day(target.isoformat(), season)
                        response = LatestGameDayResponse.model_validate(
                            collected, from_attributes=True
                        )
                        save_snapshot(session, response, season)
                        logger.info(
                            "startup_game_day_synced date=%s games=%s",
                            target,
                            len(response.games),
                        )
                    except Exception:
                        session.rollback()
                        logger.exception("startup_game_day_sync_failed date=%s", target)
            finally:
                session.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": SYNC_LOCK_NAME})
    except Exception:
        logger.exception("startup_game_day_sync_unavailable")
